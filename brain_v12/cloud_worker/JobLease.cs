namespace BrainCloudWorker;

public sealed record JobLease(
    string JobId,
    string WorkerId,
    string LeaseId,
    DateTimeOffset AcquiredAt,
    DateTimeOffset ExpiresAt,
    int Attempt);

public sealed class JobLeaseStore
{
    private readonly object _gate = new();
    private readonly Dictionary<string, JobLease> _leases = new();

    public JobLease? TryAcquire(string jobId, string workerId, TimeSpan ttl, int attempt = 1)
    {
        lock (_gate)
        {
            if (_leases.TryGetValue(jobId, out var existing) && existing.ExpiresAt > DateTimeOffset.UtcNow)
                return null;
            var lease = new JobLease(jobId, workerId, Guid.NewGuid().ToString("N"),
                DateTimeOffset.UtcNow, DateTimeOffset.UtcNow.Add(ttl), attempt);
            _leases[jobId] = lease;
            return lease;
        }
    }

    public bool Renew(string jobId, string leaseId, TimeSpan ttl)
    {
        lock (_gate)
        {
            if (!_leases.TryGetValue(jobId, out var lease) || lease.LeaseId != leaseId || lease.ExpiresAt <= DateTimeOffset.UtcNow)
                return false;
            _leases[jobId] = lease with { ExpiresAt = DateTimeOffset.UtcNow.Add(ttl) };
            return true;
        }
    }

    public bool Release(string jobId, string leaseId)
    {
        lock (_gate)
        {
            if (!_leases.TryGetValue(jobId, out var lease) || lease.LeaseId != leaseId) return false;
            _leases.Remove(jobId);
            return true;
        }
    }

    public void Expire()
    {
        lock (_gate)
        {
            var now = DateTimeOffset.UtcNow;
            foreach (var pair in _leases.Where(x => x.Value.ExpiresAt <= now).ToArray())
                _leases.Remove(pair.Key);
        }
    }
}