namespace BrainCloudWorker;

public static class WorkerRuntimeSelfTest
{
    public static void Run()
    {
        var path = Path.Combine(Path.GetTempPath(), "brain-worker-registry-" + Guid.NewGuid().ToString("N") + ".json");
        Environment.SetEnvironmentVariable("BRAIN_WORKER_REGISTRY_PATH", path);
        Environment.SetEnvironmentVariable("BRAIN_JOB_LEASE_PATH", Path.Combine(Path.GetTempPath(), "brain-worker-leases-" + Guid.NewGuid().ToString("N") + ".json"));
        try
        {
            var registry = new WorkerRegistry();
            registry.Register("test-worker", ["video", "qa"]);
            if (!registry.Heartbeat("test-worker")) throw new InvalidOperationException("heartbeat failed");
            if (registry.Snapshot().Count != 1) throw new InvalidOperationException("registration missing");

            var leases = new JobLeaseStore();
            var first = leases.TryAcquire("job-1", "test-worker", TimeSpan.FromMinutes(1))
                ?? throw new InvalidOperationException("initial lease failed");
            if (leases.TryAcquire("job-1", "other-worker", TimeSpan.FromMinutes(1)) is not null)
                throw new InvalidOperationException("duplicate active lease allowed");
            if (!leases.Renew("job-1", first.LeaseId, TimeSpan.FromMinutes(1)))
                throw new InvalidOperationException("renew failed");
            if (!leases.Release("job-1", first.LeaseId))
                throw new InvalidOperationException("release failed");
            Console.WriteLine("BRAIN_WORKER_SELF_TEST=PASS");
        }
        finally
        {
            try { File.Delete(path); } catch { }
            Environment.SetEnvironmentVariable("BRAIN_WORKER_REGISTRY_PATH", null);
            Environment.SetEnvironmentVariable("BRAIN_JOB_LEASE_PATH", null);
        }
    }
}