namespace BrainCloudWorker;
using System.Text.Json;

public sealed record WorkerRegistration(
    string WorkerId,
    string[] Capabilities,
    DateTimeOffset RegisteredAt,
    DateTimeOffset LastHeartbeat,
    string Status);

public sealed class WorkerRegistry
{
    private readonly object _gate = new();
    private readonly string _path;
    private readonly Dictionary<string, WorkerRegistration> _workers = new();

    public WorkerRegistry()
    {
        _path = Environment.GetEnvironmentVariable("BRAIN_WORKER_REGISTRY_PATH")
            ?? "/var/lib/brain/workers.json";
        Load();
    }

    public WorkerRegistration Register(string workerId, IEnumerable<string> capabilities)
    {
        var now = DateTimeOffset.UtcNow;
        var item = new WorkerRegistration(workerId, capabilities.Distinct().Order().ToArray(), now, now, "healthy");
        lock (_gate) { _workers[workerId] = item; Save(); }
        return item;
    }

    public bool Heartbeat(string workerId, string status = "healthy")
    {
        lock (_gate)
        {
            if (!_workers.TryGetValue(workerId, out var old)) return false;
            _workers[workerId] = old with { LastHeartbeat = DateTimeOffset.UtcNow, Status = status };
            Save();
            return true;
        }
    }

    public IReadOnlyList<WorkerRegistration> Snapshot()
    {
        lock (_gate) return _workers.Values.OrderBy(x => x.WorkerId).ToArray();
    }

    private void Load()
    {
        try
        {
            if (!File.Exists(_path)) return;
            var data = JsonSerializer.Deserialize<List<WorkerRegistration>>(File.ReadAllText(_path));
            if (data is null) return;
            foreach (var item in data) _workers[item.WorkerId] = item;
        }
        catch { /* fail closed: empty registry; next registration repairs state */ }
    }

    private void Save()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_path) ?? ".");
        var tmp = _path + ".tmp";
        File.WriteAllText(tmp, JsonSerializer.Serialize(_workers.Values.OrderBy(x => x.WorkerId), new JsonSerializerOptions { WriteIndented = true }));
        File.Move(tmp, _path, true);
    }
}