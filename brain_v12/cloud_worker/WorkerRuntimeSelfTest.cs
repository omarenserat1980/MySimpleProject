namespace BrainCloudWorker;

public static class WorkerRuntimeSelfTest
{
    public static void Run()
    {
        var path = Path.Combine(Path.GetTempPath(), "brain-worker-registry-" + Guid.NewGuid().ToString("N") + ".json");
        Environment.SetEnvironmentVariable("BRAIN_WORKER_REGISTRY_PATH", path);
        try
        {
            var registry = new WorkerRegistry();
            registry.Register("test-worker", ["video", "qa"]);
            if (!registry.Heartbeat("test-worker", "running")) throw new InvalidOperationException("running heartbeat failed");
            if (registry.Snapshot().Count != 1) throw new InvalidOperationException("registration missing");
            if (registry.Snapshot()[0].Status != "running") throw new InvalidOperationException("running status was not recorded");
            if (!registry.Heartbeat("test-worker", "healthy")) throw new InvalidOperationException("healthy heartbeat failed");
            if (registry.Snapshot()[0].Status != "healthy") throw new InvalidOperationException("healthy status was not recorded");
            if (!registry.Heartbeat("test-worker", "failed")) throw new InvalidOperationException("failed heartbeat failed");
            if (registry.Snapshot()[0].Status != "failed") throw new InvalidOperationException("failed status was not recorded");

            var reloadedRegistry = new WorkerRegistry();
            if (reloadedRegistry.Snapshot().Count != 1 || reloadedRegistry.Snapshot()[0].Status != "failed")
                throw new InvalidOperationException("registry status did not persist across reload");

            var leases = new JobLeaseStore();
            ExpectArgumentOutOfRange(() => leases.TryAcquire("invalid-ttl", "test-worker", TimeSpan.Zero));
            ExpectArgumentOutOfRange(() => leases.TryAcquire("invalid-attempt", "test-worker", TimeSpan.FromMinutes(1), 0));
            ExpectArgumentOutOfRange(() => leases.Renew("not-present", "lease", TimeSpan.FromHours(25)));
            var first = leases.TryAcquire("job-1", "test-worker", TimeSpan.FromMinutes(1))
                ?? throw new InvalidOperationException("initial lease failed");
            if (leases.TryAcquire("job-1", "other-worker", TimeSpan.FromMinutes(1)) is not null)
                throw new InvalidOperationException("duplicate active lease allowed");
            if (!leases.Renew("job-1", first.LeaseId, TimeSpan.FromMinutes(1)))
                throw new InvalidOperationException("renew failed");
            if (!leases.Release("job-1", first.LeaseId))
                throw new InvalidOperationException("release failed");

            VerifyBoundedTaskConsumer();
            VerifyDurableTaskQueue();
            VerifyTaskQueueCapacity();
            VerifyExpiredLeaseRecovery();
            VerifyReadinessPolicy();
            Console.WriteLine("BRAIN_WORKER_SELF_TEST=PASS");
        }
        finally
        {
            try { File.Delete(path); } catch { }
            Environment.SetEnvironmentVariable("BRAIN_WORKER_REGISTRY_PATH", null);
        }
    }

    private static void ExpectArgumentOutOfRange(Action action)
    {
        try { action(); }
        catch (ArgumentOutOfRangeException) { return; }
        throw new InvalidOperationException("invalid lease input was accepted");
    }

    private static void VerifyReadinessPolicy()
    {
        var now = DateTimeOffset.UtcNow;
        var freshSuccesses = WorkerReadinessPolicy.RequiredWorkers
            .Select(id => new WorkerPulse(id, now.AddSeconds(-10), "success", "test"))
            .ToArray();
        if (!WorkerReadinessPolicy.Evaluate(freshSuccesses, now, TimeSpan.FromMinutes(2)).Ready)
            throw new InvalidOperationException("fresh successful worker pulses should be ready");

        var withInformationalEvents = freshSuccesses
            .Concat(freshSuccesses.Select(p => p with { At = now, Status = "observe", Detail = "informational" }))
            .ToArray();
        if (!WorkerReadinessPolicy.Evaluate(withInformationalEvents, now, TimeSpan.FromMinutes(2)).Ready)
            throw new InvalidOperationException("informational events must not mask successful worker pulses");

        var missingWorker = freshSuccesses.Where(p => p.WorkerId != "mining").ToArray();
        var missingResult = WorkerReadinessPolicy.Evaluate(missingWorker, now, TimeSpan.FromMinutes(2));
        if (missingResult.Ready || missingResult.Checks["mining"]) throw new InvalidOperationException("missing worker pulse incorrectly passed readiness");

        var failedWorker = freshSuccesses.Select(p => p.WorkerId == "video" ? p with { Status = "failed" } : p).ToArray();
        var failedResult = WorkerReadinessPolicy.Evaluate(failedWorker, now, TimeSpan.FromMinutes(2));
        if (failedResult.Ready || failedResult.Checks["video"]) throw new InvalidOperationException("failed worker incorrectly passed readiness");

        var staleWorker = freshSuccesses.Select(p => p.WorkerId == "quality" ? p with { At = now.AddMinutes(-3) } : p).ToArray();
        var staleResult = WorkerReadinessPolicy.Evaluate(staleWorker, now, TimeSpan.FromMinutes(2));
        if (staleResult.Ready || staleResult.Checks["quality"]) throw new InvalidOperationException("stale worker pulse incorrectly passed readiness");

        var futureWorker = freshSuccesses.Select(p => p.WorkerId == "health" ? p with { At = now.AddSeconds(30) } : p).ToArray();
        var futureResult = WorkerReadinessPolicy.Evaluate(futureWorker, now, TimeSpan.FromMinutes(2));
        if (futureResult.Ready || futureResult.Checks["health"]) throw new InvalidOperationException("future-dated worker pulse incorrectly passed readiness");

        var olderFailureAfterSuccess = freshSuccesses.Append(new WorkerPulse("mining", now.AddMinutes(-1), "failed", "older failure")).ToArray();
        if (!WorkerReadinessPolicy.Evaluate(olderFailureAfterSuccess, now, TimeSpan.FromMinutes(2)).Ready)
            throw new InvalidOperationException("older pulse should not override the latest pulse");

        var healthyRegistry = WorkerReadinessPolicy.RequiredWorkers
            .Select(id => new WorkerRegistryEntry(new WorkerRegistration(id, [id], now.AddSeconds(-20), now.AddSeconds(-5), "healthy"), true, "healthy"))
            .ToArray();
        if (!WorkerReadinessPolicy.Evaluate(freshSuccesses, healthyRegistry, now, TimeSpan.FromMinutes(2)).Ready)
            throw new InvalidOperationException("fresh pulses and healthy registry heartbeats should be ready");

        var missingRegistration = healthyRegistry.Where(entry => entry.Registration.WorkerId != "mining").ToArray();
        var missingRegistrationResult = WorkerReadinessPolicy.Evaluate(freshSuccesses, missingRegistration, now, TimeSpan.FromMinutes(2));
        if (missingRegistrationResult.Ready || missingRegistrationResult.Checks["mining"]) throw new InvalidOperationException("missing registry entry incorrectly passed readiness");

        var staleRegistration = healthyRegistry.Select(entry => entry.Registration.WorkerId == "video" ? entry with { Fresh = false, EffectiveStatus = "stale" } : entry).ToArray();
        var staleRegistrationResult = WorkerReadinessPolicy.Evaluate(freshSuccesses, staleRegistration, now, TimeSpan.FromMinutes(2));
        if (staleRegistrationResult.Ready || staleRegistrationResult.Checks["video"]) throw new InvalidOperationException("stale registry heartbeat incorrectly passed readiness");

        var failedRegistration = healthyRegistry.Select(entry => entry.Registration.WorkerId == "quality" ? entry with { EffectiveStatus = "failed" } : entry).ToArray();
        var failedRegistrationResult = WorkerReadinessPolicy.Evaluate(freshSuccesses, failedRegistration, now, TimeSpan.FromMinutes(2));
        if (failedRegistrationResult.Ready || failedRegistrationResult.Checks["quality"]) throw new InvalidOperationException("failed registry status incorrectly passed readiness");
    }


    private static void VerifyBoundedTaskConsumer()
    {
        var path = Path.Combine(Path.GetTempPath(), "brain-consumer-" + Guid.NewGuid().ToString("N") + ".json");
        try
        {
            var queue = new DurableFileTaskQueue(path);
            using var loggerFactory = LoggerFactory.Create(builder => builder.SetMinimumLevel(LogLevel.Warning));
            var logger = loggerFactory.CreateLogger("BoundedTaskConsumerSelfTest");

            var health = queue.Submit("self-test", "consumer-health", "health_check", "{}").Task;
            var healthLease = queue.TryLeaseNext("self-test-consumer", TimeSpan.FromMinutes(1))
                ?? throw new InvalidOperationException("health task could not be leased");
            if (!BoundedTaskConsumer.ProcessLeasedTask(queue, healthLease, logger))
                throw new InvalidOperationException("bounded consumer did not complete health task");
            var healthResult = queue.Snapshot().Single(t => t.TaskId == health.TaskId);
            if (healthResult.Status != "succeeded" || healthResult.ResultJson is null ||
                !healthResult.ResultJson.Contains("LOCAL_QUEUE_CHECK_ONLY", StringComparison.Ordinal) ||
                !healthResult.ResultJson.Contains("\"external_runtime_verified\":false", StringComparison.Ordinal))
                throw new InvalidOperationException("health task result overstated external verification");

            var simulation = queue.Submit("self-test", "consumer-simulation", "simulation_status", "{}").Task;
            var simulationLease = queue.TryLeaseNext("self-test-consumer", TimeSpan.FromMinutes(1))
                ?? throw new InvalidOperationException("simulation task could not be leased");
            if (!BoundedTaskConsumer.ProcessLeasedTask(queue, simulationLease, logger))
                throw new InvalidOperationException("bounded consumer did not complete simulation task");
            var simulationResult = queue.Snapshot().Single(t => t.TaskId == simulation.TaskId);
            if (simulationResult.Status != "succeeded" || simulationResult.ResultJson is null ||
                !simulationResult.ResultJson.Contains("\"mode\":\"SIMULATOR\"", StringComparison.Ordinal) ||
                !simulationResult.ResultJson.Contains("\"network_access_performed\":false", StringComparison.Ordinal) ||
                !simulationResult.ResultJson.Contains("\"real_mining_verified\":false", StringComparison.Ordinal) ||
                !simulationResult.ResultJson.Contains("\"accepted_shares_verified\":false", StringComparison.Ordinal) ||
                !simulationResult.ResultJson.Contains("\"revenue_verified\":false", StringComparison.Ordinal))
                throw new InvalidOperationException("simulation result overstated real mining or revenue evidence");
        }
        finally
        {
            try { File.Delete(path); } catch { }
        }
    }

    private static void VerifyDurableTaskQueue()
    {
        var path = Path.Combine(Path.GetTempPath(), "brain-task-queue-" + Guid.NewGuid().ToString("N") + ".json");
        try
        {
            var queue = new DurableFileTaskQueue(path);
            var first = queue.Submit("self-test", "idem-1", "health_check", """{"probe":"local"}""");
            if (first.Duplicate || first.Task.Status != "queued")
                throw new InvalidOperationException("new durable task was not queued");

            var duplicate = queue.Submit("self-test", "idem-1", "health_check", """{ "probe" : "local" }""");
            if (!duplicate.Duplicate || duplicate.Task.TaskId != first.Task.TaskId)
                throw new InvalidOperationException("idempotent submission did not return the original task");

            try
            {
                queue.Submit("self-test", "idem-1", "simulation_status", "{}");
                throw new InvalidOperationException("idempotency key payload conflict was accepted");
            }
            catch (InvalidOperationException ex) when (ex.Message == "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT") { }

            try
            {
                queue.Submit("self-test", "idem-2", "shell", """{"cmd":"echo unsafe"}""");
                throw new InvalidOperationException("non-allow-listed task type was accepted");
            }
            catch (ArgumentException) { }

            var lease = queue.TryLeaseNext("test-worker", TimeSpan.FromMinutes(1))
                ?? throw new InvalidOperationException("queued task could not be leased");
            if (lease.TaskId != first.Task.TaskId || lease.LeaseId is null)
                throw new InvalidOperationException("lease metadata was not recorded");
            if (!queue.Complete(lease.TaskId, lease.LeaseId, """{"ok":true}"""))
                throw new InvalidOperationException("valid lease could not complete task");
            if (queue.Complete(lease.TaskId, lease.LeaseId, """{"ok":true}"""))
                throw new InvalidOperationException("completed task accepted a stale completion");

            var reloaded = new DurableFileTaskQueue(path);
            var persisted = reloaded.Snapshot().Single(t => t.TaskId == first.Task.TaskId);
            if (persisted.Status != "succeeded" || persisted.ResultJson is null)
                throw new InvalidOperationException("task result did not persist across queue reload");
            if (!reloaded.AuditSnapshot().Any(e => e.TaskId == first.Task.TaskId && e.Event == "succeeded"))
                throw new InvalidOperationException("completion audit event was not persisted");
        }
        finally
        {
            try { File.Delete(path); } catch { }
        }
    }

    private static void VerifyTaskQueueCapacity()
    {
        var path = Path.Combine(Path.GetTempPath(), "brain-task-capacity-" + Guid.NewGuid().ToString("N") + ".json");
        try
        {
            var queue = new DurableFileTaskQueue(path, maxTaskRecords: 2);
            queue.Submit("self-test", "capacity-1", "health_check", "{}");
            queue.Submit("self-test", "capacity-2", "simulation_status", "{}");

            try
            {
                queue.Submit("self-test", "capacity-3", "health_check", "{}");
                throw new InvalidOperationException("task queue accepted records beyond its configured capacity");
            }
            catch (InvalidOperationException ex) when (ex.Message == "TASK_QUEUE_CAPACITY_REACHED") { }

            // Existing idempotent retries must still work at capacity.
            var duplicate = queue.Submit("self-test", "capacity-1", "health_check", "{}");
            if (!duplicate.Duplicate || queue.Snapshot().Count != 2)
                throw new InvalidOperationException("queue capacity broke idempotent retries");
        }
        finally
        {
            try { File.Delete(path); } catch { }
        }
    }

    private sealed class ManualTimeProvider(DateTimeOffset now) : TimeProvider
    {
        private DateTimeOffset _now = now;
        public override DateTimeOffset GetUtcNow() => _now;
        public void Advance(TimeSpan duration) => _now = _now.Add(duration);
    }

    private static void VerifyExpiredLeaseRecovery()
    {
        var path = Path.Combine(Path.GetTempPath(), "brain-task-expiry-" + Guid.NewGuid().ToString("N") + ".json");
        var clock = new ManualTimeProvider(DateTimeOffset.Parse("2026-01-01T00:00:00Z"));
        try
        {
            var queue = new DurableFileTaskQueue(path, clock);
            var submitted = queue.Submit("self-test", "expiry-1", "health_check", """{"probe":"expiry"}""");
            var firstLease = queue.TryLeaseNext("worker-old", TimeSpan.FromMinutes(1))
                ?? throw new InvalidOperationException("initial expiry-test lease failed");
            clock.Advance(TimeSpan.FromMinutes(2));

            var secondLease = queue.TryLeaseNext("worker-new", TimeSpan.FromMinutes(1))
                ?? throw new InvalidOperationException("expired task was not requeued and leased");
            if (secondLease.TaskId != submitted.Task.TaskId || secondLease.Attempt != 2 ||
                secondLease.WorkerId != "worker-new" || secondLease.LeaseId == firstLease.LeaseId)
                throw new InvalidOperationException("expired lease was not replaced with a fresh second lease");

            if (queue.Complete(firstLease.TaskId, firstLease.LeaseId!, """{"ok":true}"""))
                throw new InvalidOperationException("old worker completed task after lease expiry");
            if (!queue.Complete(secondLease.TaskId, secondLease.LeaseId!, """{"ok":true}"""))
                throw new InvalidOperationException("current lease could not complete recovered task");

            var reloaded = new DurableFileTaskQueue(path, clock);
            if (reloaded.Snapshot().Single(t => t.TaskId == submitted.Task.TaskId).Status != "succeeded")
                throw new InvalidOperationException("recovered task result did not persist");
            if (!reloaded.AuditSnapshot().Any(e => e.TaskId == submitted.Task.TaskId && e.Event == "lease_expired_requeued"))
                throw new InvalidOperationException("lease-expiry recovery was not audited");
        }
        finally
        {
            try { File.Delete(path); } catch { }
        }
    }
}
