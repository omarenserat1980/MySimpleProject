using System.Text.Json;

namespace BrainCloudWorker;

public sealed record WorkerHeartbeat(
    string WorkerId,
    DateTimeOffset At,
    string Status,
    string Detail);

public sealed class WorkerHeartbeatStore
{
    private readonly object _gate = new();
    private readonly string _path;
    public WorkerHeartbeatStore()
    {
        _path = Environment.GetEnvironmentVariable("BRAIN_HEARTBEAT_PATH")
            ?? "/var/lib/brain/worker-heartbeat.json";
        Directory.CreateDirectory(Path.GetDirectoryName(_path) ?? ".");
    }

    public void Write(WorkerHeartbeat heartbeat)
    {
        lock (_gate)
        {
            var temp = _path + ".tmp";
            File.WriteAllText(temp, JsonSerializer.Serialize(heartbeat, new JsonSerializerOptions { WriteIndented = true }));
            File.Move(temp, _path, true);
        }
    }
}
