namespace BrainCloudWorker;

public sealed record WorkerReadinessResult(bool Ready, IReadOnlyDictionary<string, bool> Checks);

public static class WorkerReadinessPolicy
{
    public static readonly string[] RequiredWorkers =
    [
        "supervisor", "video", "mining", "quality", "self-healing",
        "research", "architect", "economic", "health"
    ];

    public static WorkerReadinessResult Evaluate(
        IEnumerable<WorkerPulse> pulses,
        DateTimeOffset now,
        TimeSpan maxAge)
    {
        if (maxAge <= TimeSpan.Zero)
            throw new ArgumentOutOfRangeException(nameof(maxAge), "Maximum pulse age must be positive.");

        var cutoff = now - maxAge;
        // Worker details such as "observe" and "verify" are informational
        // events emitted after a successful tick. Only lifecycle outcomes
        // participate in readiness, so those details cannot mask a success.
        var latest = pulses
            .Where(p => p.Status is "running" or "success" or "failed")
            .GroupBy(p => p.WorkerId)
            .ToDictionary(g => g.Key, g => g.OrderByDescending(p => p.At).First());

        var checks = RequiredWorkers.ToDictionary(
            id => id,
            id => latest.TryGetValue(id, out var pulse)
                && pulse.Status == "success"
                && pulse.At <= now
                && pulse.At >= cutoff);

        return new WorkerReadinessResult(checks.Values.All(passed => passed), checks);
    }

    // Readiness requires both a fresh successful work pulse and a fresh,
    // healthy registry heartbeat. Either source alone is insufficient.
    public static WorkerReadinessResult Evaluate(
        IEnumerable<WorkerPulse> pulses,
        IEnumerable<WorkerRegistryEntry> registryEntries,
        DateTimeOffset now,
        TimeSpan maxAge)
    {
        var pulseResult = Evaluate(pulses, now, maxAge);
        var registry = registryEntries
            .GroupBy(entry => entry.Registration.WorkerId)
            .ToDictionary(group => group.Key, group => group.OrderByDescending(
                entry => entry.Registration.LastHeartbeat).First());

        var checks = RequiredWorkers.ToDictionary(
            id => id,
            id => pulseResult.Checks[id]
                && registry.TryGetValue(id, out var entry)
                && entry.Fresh
                && entry.EffectiveStatus == "healthy"
                && entry.Registration.LastHeartbeat <= now
                && entry.Registration.LastHeartbeat >= now - maxAge);

        return new WorkerReadinessResult(checks.Values.All(passed => passed), checks);
    }
}
