using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace BrainCloudWorker;

public sealed record DurableTaskRecord(
    string TaskId,
    string Principal,
    string IdempotencyKey,
    string PayloadHash,
    string TaskType,
    string ArgumentsJson,
    string Status,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    string? LeaseId = null,
    string? WorkerId = null,
    DateTimeOffset? LeaseExpiresAt = null,
    int Attempt = 0,
    string? ResultJson = null,
    string? ErrorCode = null);

public sealed record DurableTaskAuditEvent(
    string TaskId,
    string Event,
    DateTimeOffset At,
    string Principal,
    string? Detail = null);

internal sealed record DurableTaskQueueSnapshot(
    int Version,
    List<DurableTaskRecord> Tasks,
    List<DurableTaskAuditEvent> Audit);

public sealed record TaskSubmissionResult(DurableTaskRecord Task, bool Duplicate);

/// <summary>
/// Crash-safe, atomic-file task queue for a single process and single writer.
/// This is not a distributed or multi-process queue; do not use across replicas.
/// </summary>
public sealed class DurableFileTaskQueue
{
    private const int SchemaVersion = 1;
    private const int MaxArgumentsBytes = 16 * 1024;
    private const int MaxIdempotencyKeyLength = 128;
    private const int MaxAuditEntries = 10_000;
    private static readonly TimeSpan MaxLeaseTtl = TimeSpan.FromHours(24);
    private static readonly HashSet<string> AllowedTaskTypes = new(StringComparer.Ordinal)
    {
        "health_check",
        "simulation_status"
    };

    private readonly object _gate = new();
    private readonly string _path;
    private readonly TimeProvider _clock;

    public DurableFileTaskQueue(string path, TimeProvider? clock = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        _path = Path.GetFullPath(path);
        _clock = clock ?? TimeProvider.System;
        Directory.CreateDirectory(Path.GetDirectoryName(_path)!);
        lock (_gate) _ = ReadSnapshot();
    }

    public TaskSubmissionResult Submit(string principal, string idempotencyKey, string taskType, string argumentsJson)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(principal);
        ArgumentException.ThrowIfNullOrWhiteSpace(idempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(taskType);
        ArgumentNullException.ThrowIfNull(argumentsJson);
        if (idempotencyKey.Length > MaxIdempotencyKeyLength)
            throw new ArgumentOutOfRangeException(nameof(idempotencyKey), "Idempotency key is too long.");
        if (!AllowedTaskTypes.Contains(taskType))
            throw new ArgumentException("Task type is not allow-listed.", nameof(taskType));
        if (Encoding.UTF8.GetByteCount(argumentsJson) > MaxArgumentsBytes)
            throw new ArgumentOutOfRangeException(nameof(argumentsJson), "Task arguments exceed the size limit.");
        using (JsonDocument.Parse(argumentsJson)) { }

        var canonical = JsonSerializer.Serialize(new { taskType, arguments = JsonDocument.Parse(argumentsJson).RootElement });
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(canonical)));
        lock (_gate)
        {
            var snapshot = ReadSnapshot();
            var existing = snapshot.Tasks.FirstOrDefault(t =>
                t.Principal == principal && t.IdempotencyKey == idempotencyKey);
            if (existing is not null)
            {
                if (!CryptographicOperations.FixedTimeEquals(
                    Convert.FromHexString(existing.PayloadHash), Convert.FromHexString(hash)))
                    throw new InvalidOperationException("IDEMPOTENCY_KEY_PAYLOAD_CONFLICT");
                return new TaskSubmissionResult(existing, true);
            }

            var now = _clock.GetUtcNow();
            var task = new DurableTaskRecord(Guid.NewGuid().ToString("N"), principal, idempotencyKey,
                hash, taskType, JsonSerializer.Serialize(JsonDocument.Parse(argumentsJson).RootElement),
                "queued", now, now);
            snapshot.Tasks.Add(task);
            snapshot.Audit.Add(new DurableTaskAuditEvent(task.TaskId, "queued", now, principal));
            WriteSnapshot(snapshot);
            return new TaskSubmissionResult(task, false);
        }
    }

    public DurableTaskRecord? TryLeaseNext(string workerId, TimeSpan ttl)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(workerId);
        ValidateTtl(ttl);
        lock (_gate)
        {
            var snapshot = ReadSnapshot();
            var now = _clock.GetUtcNow();
            var index = snapshot.Tasks.FindIndex(t => t.Status == "queued");
            if (index < 0) return null;
            var current = snapshot.Tasks[index];
            var leased = current with
            {
                Status = "leased",
                WorkerId = workerId,
                LeaseId = Guid.NewGuid().ToString("N"),
                LeaseExpiresAt = now.Add(ttl),
                Attempt = checked(current.Attempt + 1),
                UpdatedAt = now
            };
            snapshot.Tasks[index] = leased;
            snapshot.Audit.Add(new DurableTaskAuditEvent(leased.TaskId, "leased", now, current.Principal, workerId));
            WriteSnapshot(snapshot);
            return leased;
        }
    }

    public bool Complete(string taskId, string leaseId, string resultJson)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(taskId);
        ArgumentException.ThrowIfNullOrWhiteSpace(leaseId);
        ArgumentNullException.ThrowIfNull(resultJson);
        if (Encoding.UTF8.GetByteCount(resultJson) > MaxArgumentsBytes)
            throw new ArgumentOutOfRangeException(nameof(resultJson), "Result exceeds the size limit.");
        using (JsonDocument.Parse(resultJson)) { }

        lock (_gate)
        {
            var snapshot = ReadSnapshot();
            var index = snapshot.Tasks.FindIndex(t => t.TaskId == taskId);
            if (index < 0) return false;
            var current = snapshot.Tasks[index];
            var now = _clock.GetUtcNow();
            if (current.Status != "leased" || current.LeaseId != leaseId ||
                current.LeaseExpiresAt is null || current.LeaseExpiresAt <= now)
                return false;
            var completed = current with
            {
                Status = "succeeded",
                ResultJson = resultJson,
                UpdatedAt = now,
                LeaseId = null,
                LeaseExpiresAt = null
            };
            snapshot.Tasks[index] = completed;
            snapshot.Audit.Add(new DurableTaskAuditEvent(taskId, "succeeded", now, current.Principal));
            WriteSnapshot(snapshot);
            return true;
        }
    }

    public IReadOnlyList<DurableTaskRecord> Snapshot()
    {
        lock (_gate) return ReadSnapshot().Tasks.ToArray();
    }

    public IReadOnlyList<DurableTaskAuditEvent> AuditSnapshot()
    {
        lock (_gate) return ReadSnapshot().Audit.ToArray();
    }

    private DurableTaskQueueSnapshot ReadSnapshot()
    {
        if (!File.Exists(_path)) return new DurableTaskQueueSnapshot(SchemaVersion, [], []);
        var json = File.ReadAllText(_path);
        var snapshot = JsonSerializer.Deserialize<DurableTaskQueueSnapshot>(json)
            ?? throw new InvalidDataException("Task queue snapshot is empty or invalid.");
        if (snapshot.Version != SchemaVersion || snapshot.Tasks is null || snapshot.Audit is null)
            throw new InvalidDataException("Unsupported task queue schema.");
        return snapshot;
    }

    private void WriteSnapshot(DurableTaskQueueSnapshot snapshot)
    {
        if (snapshot.Audit.Count > MaxAuditEntries)
            snapshot.Audit.RemoveRange(0, snapshot.Audit.Count - MaxAuditEntries);
        var temp = _path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            var bytes = JsonSerializer.SerializeToUtf8Bytes(snapshot);
            using (var stream = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                stream.Write(bytes);
                stream.Flush(flushToDisk: true);
            }
            File.Move(temp, _path, overwrite: true);
        }
        finally
        {
            try { if (File.Exists(temp)) File.Delete(temp); } catch { }
        }
    }

    private static void ValidateTtl(TimeSpan ttl)
    {
        if (ttl <= TimeSpan.Zero || ttl > MaxLeaseTtl)
            throw new ArgumentOutOfRangeException(nameof(ttl), "Lease TTL must be greater than zero and no more than 24 hours.");
    }
}
