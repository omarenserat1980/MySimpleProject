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
            if (registry.Snapshot()[0].Status != "running")
                throw new InvalidOperationException("running status was not recorded");
            if (!registry.Heartbeat("test-worker", "healthy")) throw new InvalidOperationException("healthy heartbeat failed");
            if (registry.Snapshot()[0].Status != "healthy")
                throw new InvalidOperationException("healthy status was not recorded");
            if (!registry.Heartbeat("test-worker", "failed")) throw new InvalidOperationException("failed heartbeat failed");
            if (registry.Snapshot()[0].Status != "failed")
                throw new InvalidOperationException("failed status was not recorded");

            var reloadedRegistry = new WorkerRegistry();
            if (reloadedRegistry.Snapshot().Count != 1 || reloadedRegistry.Snapshot()[0].Status != "failed")
                throw new InvalidOperationException("registry status did not persist across reload");

            var leases = new JobLeaseStore();
            var first = leases.TryAcquire("job-1", "test-worker", TimeSpan.FromMinutes(1))
                ?? throw new InvalidOperationException("initial lease failed");
            if (leases.TryAcquire("job-1", "other-worker", TimeSpan.FromMinutes(1)) is not null)
                throw new InvalidOperationException("duplicate active lease allowed");
            if (!leases.Renew("job-1", first.LeaseId, TimeSpan.FromMinutes(1)))
                throw new InvalidOperationException("renew failed");
            if (!leases.Release("job-1", first.LeaseId))
                throw new InvalidOperationException("release failed");

            VerifyReadinessPolicy();
            Console.WriteLine("BRAIN_WORKER_SELF_TEST=PASS");
        }
        finally
        {
            try { File.Delete(path); } catch { }
            Environment.SetEnvironmentVariable("BRAIN_WORKER_REGISTRY_PATH", null);
        }
    }

    private static void VerifyReadinessPolicy()
    {
        var now = DateTimeOffset.UtcNow;
        var freshSuccesses = WorkerReadinessPolicy.RequiredWorkers
            .Select(id => new WorkerPulse(id, now.AddSeconds(-10), "success", "test"));

        if (!WorkerReadinessPolicy.Evaluate(freshSuccesses, now, TimeSpan.FromMinutes(2)).Ready)
            throw new InvalidOperationException("fresh successful worker pulses should be ready");

        var missingWorker = freshSuccesses.Where(p => p.WorkerId != "mining").ToArray();
        var missingResult = WorkerReadinessPolicy.Evaluate(missingWorker, now, TimeSpan.FromMinutes(2));
        if (missingResult.Ready || missingResult.Checks["mining"])
            throw new InvalidOperationException("missing worker pulse incorrectly passed readiness");

        var failedWorker = freshSuccesses
            .Select(p => p.WorkerId == "video" ? p with { Status = "failed" } : p)
            .ToArray();
        var failedResult = WorkerReadinessPolicy.Evaluate(failedWorker, now, TimeSpan.FromMinutes(2));
        if (failedResult.Ready || failedResult.Checks["video"])
            throw new InvalidOperationException("failed worker incorrectly passed readiness");

        var staleWorker = freshSuccesses
            .Select(p => p.WorkerId == "quality" ? p with { At = now.AddMinutes(-3) } : p)
            .ToArray();
        var staleResult = WorkerReadinessPolicy.Evaluate(staleWorker, now, TimeSpan.FromMinutes(2));
        if (staleResult.Ready || staleResult.Checks["quality"])
            throw new InvalidOperationException("stale worker pulse incorrectly passed readiness");

        var futureWorker = freshSuccesses
            .Select(p => p.WorkerId == "health" ? p with { At = now.AddSeconds(30) } : p)
            .ToArray();
        var futureResult = WorkerReadinessPolicy.Evaluate(futureWorker, now, TimeSpan.FromMinutes(2));
        if (futureResult.Ready || futureResult.Checks["health"])
            throw new InvalidOperationException("future-dated worker pulse incorrectly passed readiness");

        var olderFailureAfterSuccess = freshSuccesses
            .Append(new WorkerPulse("mining", now.AddMinutes(-1), "failed", "older failure"))
            .ToArray();
        if (!WorkerReadinessPolicy.Evaluate(olderFailureAfterSuccess, now, TimeSpan.FromMinutes(2)).Ready)
            throw new InvalidOperationException("older pulse should not override the latest pulse");
    }
}
