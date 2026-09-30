namespace BrainCloudWorker;
using System.Text.Json;

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
    private readonly string _path;
    private readonly Dictionary<string, JobLease> _leases = new();

    public JobLeaseStore()
    {
        _path = Environment.GetEnvironmentVariable("BRAIN_JOB_LEASE_PATH")
            ?? "/var/lib/brain/job-leases.json";
        Load();
    }

    public JobLease? TryAcquire(string jobId, string workerId, TimeSpan ttl, int attempt = 1)
    {
        lock (_gate)
        {
            ExpireInternal();
            if (_leases.ContainsKey(jobId)) return null;
            var now = DateTimeOffset.UtcNow;
            var lease = new JobLease(jobId, workerId, Guid.NewGuid().ToString("N"),
                now, now.Add(ttl), attempt);
            _leases[jobId] = lease;
            Save();
            return lease;
        }
    }

    public bool Renew(string jobId, string leaseId, TimeSpan ttl)
    {
        lock (_gate)
        {
            ExpireInternal();
            if (!_leases.TryGetValue(jobId, out var lease) || lease.LeaseId != leaseId) return false;
            _leases[jobId] = lease with { ExpiresAt = DateTimeOffset.UtcNow.Add(ttl) };
            Save();
            return true;
        }
    }

    public bool Release(string jobId, string leaseId)
    {
        lock (_gate)
        {
            if (!_leases.TryGetValue(jobId, out var lease) || lease.LeaseId != leaseId) return false;
            _leases.Remove(jobId);
            Save();
            return true;
        }
    }

    public IReadOnlyList<JobLease> Snapshot()
    {
        lock (_gate) return _leases.Values.OrderBy(x => x.JobId).ToArray();
    }

    public void Expire()
    {
        lock (_gate) { ExpireInternal(); Save(); }
    }

    private void ExpireInternal()
    {
        var now = DateTimeOffset.UtcNow;
        foreach (var pair in _leases.Where(x => x.Value.ExpiresAt <= now).ToArray())
            _leases.Remove(pair.Key);
    }

    private void Load()
    {
        try
        {
            if (!File.Exists(_path)) return;
            var data = JsonSerializer.Deserialize<List<JobLease>>(File.ReadAllText(_path));
            if (data is null) return;
            foreach (var item in data.Where(x => x.ExpiresAt > DateTimeOffset.UtcNow))
                _leases[item.JobId] = item;
        }
        catch
        {
            // Fail closed: an unreadable lease file results in no active leases.
            _leases.Clear();
        }
    }

    private void Save()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_path) ?? ".");
        var tmp = _path + ".tmp";
        File.WriteAllText(tmp, JsonSerializer.Serialize(_leases.Values.OrderBy(x => x.JobId),
            new JsonSerializerOptions { WriteIndented = true }));
        File.Move(tmp, _path, true);
    }
}
