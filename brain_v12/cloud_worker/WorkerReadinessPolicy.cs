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
        var latest = pulses
            .GroupBy(p => p.WorkerId)
            .ToDictionary(g => g.Key, g => g.OrderByDescending(p => p.At).First());

        var checks = RequiredWorkers.ToDictionary(
            id => id,
            id => latest.TryGetValue(id, out var pulse)
                && pulse.Status == "success"
                && pulse.At <= now
                && pulse.At >= cutoff);

        return new WorkerReadinessResult(
            checks.Values.All(passed => passed),
            checks);
    }
}
