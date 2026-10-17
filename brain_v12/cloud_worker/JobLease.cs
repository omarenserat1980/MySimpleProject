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
        ArgumentException.ThrowIfNullOrWhiteSpace(jobId);
        ArgumentException.ThrowIfNullOrWhiteSpace(workerId);
        ValidateTtl(ttl);
        if (attempt < 1) throw new ArgumentOutOfRangeException(nameof(attempt), "Attempt must be at least one.");

        lock (_gate)
        {
            if (_leases.TryGetValue(jobId, out var existing) && existing.ExpiresAt > DateTimeOffset.UtcNow)
                return null;
            var now = DateTimeOffset.UtcNow;
            var lease = new JobLease(jobId, workerId, Guid.NewGuid().ToString("N"),
                now, now.Add(ttl), attempt);
            _leases[jobId] = lease;
            return lease;
        }
    }

    public bool Renew(string jobId, string leaseId, TimeSpan ttl)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(jobId);
        ArgumentException.ThrowIfNullOrWhiteSpace(leaseId);
        ValidateTtl(ttl);
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
        ArgumentException.ThrowIfNullOrWhiteSpace(jobId);
        ArgumentException.ThrowIfNullOrWhiteSpace(leaseId);
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

    private static void ValidateTtl(TimeSpan ttl)
    {
        if (ttl <= TimeSpan.Zero || ttl > TimeSpan.FromHours(24))
            throw new ArgumentOutOfRangeException(nameof(ttl), "Lease TTL must be greater than zero and no more than 24 hours.");
    }
}
