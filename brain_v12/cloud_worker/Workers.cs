namespace BrainCloudWorker;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

public sealed record WorkerPulse(string WorkerId, DateTimeOffset At, string Status, string Detail);

public sealed class WorkerState(WorkerHeartbeatStore heartbeat)
{
    private readonly object _gate = new();
    private readonly List<WorkerPulse> _pulses = [];

    public void Record(string id, string status, string detail)
    {
        var pulse = new WorkerPulse(id, DateTimeOffset.UtcNow, status, detail);
        lock (_gate)
        {
            _pulses.Add(pulse);
            if (_pulses.Count > 500) _pulses.RemoveRange(0, _pulses.Count - 500);
        }
        heartbeat.Write(new WorkerHeartbeat(id, pulse.At, status, detail));
    }

    public IReadOnlyList<WorkerPulse> Snapshot()
    {
        lock (_gate) return _pulses.ToArray();
    }
}

public abstract class BrainPeriodicWorker(
    string id,
    TimeSpan interval,
    WorkerState state,
    WorkerRegistry registry,
    ILogger logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        // Registration is explicit and separate from pulse-based readiness.
        // A worker is visible in the registry only after its hosted service starts.
        registry.Register(id, [id]);
        logger.LogInformation("Brain worker {WorkerId} started; interval={Interval}", id, interval);

        using var timer = new PeriodicTimer(interval);
        await TickAsync(ct);
        while (await timer.WaitForNextTickAsync(ct)) await TickAsync(ct);
    }

    private async Task TickAsync(CancellationToken ct)
    {
        try
        {
            state.Record(id, "running", "tick_started");
            registry.Heartbeat(id, "running");
            await ExecuteTickAsync(ct);
            state.Record(id, "success", "tick_completed");
            registry.Heartbeat(id, "healthy");
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested)
        {
            registry.Heartbeat(id, "stopping");
        }
        catch (Exception ex)
        {
            state.Record(id, "failed", ex.GetType().Name + ":" + ex.Message);
            registry.Heartbeat(id, "failed");
            logger.LogError(ex, "Worker {WorkerId} tick failed", id);
        }
    }

    protected abstract Task ExecuteTickAsync(CancellationToken ct);
}

public sealed class BrainSupervisorWorker(WorkerState s, WorkerRegistry r, ILogger<BrainSupervisorWorker> l)
    : BrainPeriodicWorker("supervisor", TimeSpan.FromSeconds(5), s, r, l)
{
    protected override Task ExecuteTickAsync(CancellationToken ct)
    {
        s.Record("supervisor", "observe", "coordinates_workers;no_external_side_effects");
        return Task.CompletedTask;
    }
}

public sealed class VideoWorker(WorkerState s, WorkerRegistry r, ILogger<VideoWorker> l)
    : BrainPeriodicWorker("video", TimeSpan.FromSeconds(15), s, r, l)
{
    protected override Task ExecuteTickAsync(CancellationToken ct)
    {
        s.Record("video", "observe", "uses_existing_film_supervisor;does_not_duplicate_renderer");
        return Task.CompletedTask;
    }
}

public sealed class MiningWorker(WorkerState s, WorkerRegistry r, ILogger<MiningWorker> l)
    : BrainPeriodicWorker("mining", TimeSpan.FromSeconds(30), s, r, l)
{
    protected override Task ExecuteTickAsync(CancellationToken ct)
    {
        s.Record("mining", "observe", "registered_workers_only;github_actions_mining_forbidden");
        return Task.CompletedTask;
    }
}

public sealed class QualityWorker(WorkerState s, WorkerRegistry r, ILogger<QualityWorker> l)
    : BrainPeriodicWorker("quality", TimeSpan.FromSeconds(10), s, r, l)
{
    protected override Task ExecuteTickAsync(CancellationToken ct)
    {
        s.Record("quality", "verify", "evidence_first;workflow_green_is_not_success");
        return Task.CompletedTask;
    }
}

public sealed class SelfHealingWorker(WorkerState s, WorkerRegistry r, ILogger<SelfHealingWorker> l)
    : BrainPeriodicWorker("self-healing", TimeSpan.FromSeconds(15), s, r, l)
{
    protected override Task ExecuteTickAsync(CancellationToken ct)
    {
        s.Record("self-healing", "observe", "bounded_repair_only;control_plane_limits_attempts");
        return Task.CompletedTask;
    }
}

public sealed class ResearchWorker(WorkerState s, WorkerRegistry r, ILogger<ResearchWorker> l)
    : BrainPeriodicWorker("research", TimeSpan.FromHours(2), s, r, l)
{
    protected override Task ExecuteTickAsync(CancellationToken ct)
    {
        s.Record("research", "observe", "research_only;changes_require_verification");
        return Task.CompletedTask;
    }
}

public sealed class ArchitectWorker(WorkerState s, WorkerRegistry r, ILogger<ArchitectWorker> l)
    : BrainPeriodicWorker("architect", TimeSpan.FromHours(4), s, r, l)
{
    protected override Task ExecuteTickAsync(CancellationToken ct)
    {
        s.Record("architect", "observe", "architecture_review;no_unbounded_self_modification");
        return Task.CompletedTask;
    }
}

public sealed class EconomicWorker(WorkerState s, WorkerRegistry r, ILogger<EconomicWorker> l)
    : BrainPeriodicWorker("economic", TimeSpan.FromMinutes(5), s, r, l)
{
    protected override Task ExecuteTickAsync(CancellationToken ct)
    {
        s.Record("economic", "observe", "discovery_and_ledger_only;verified_payment_required");
        return Task.CompletedTask;
    }
}

public sealed class HealthWorker(WorkerState s, WorkerRegistry r, ILogger<HealthWorker> l)
    : BrainPeriodicWorker("health", TimeSpan.FromSeconds(15), s, r, l)
{
    protected override Task ExecuteTickAsync(CancellationToken ct)
    {
        s.Record("health", "observe", "runtime_health_and_worker_liveness");
        return Task.CompletedTask;
    }
}
