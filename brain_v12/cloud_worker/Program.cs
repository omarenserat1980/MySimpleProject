using BrainCloudWorker;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;

if (args.Contains("--self-test", StringComparer.OrdinalIgnoreCase))
{
    WorkerRuntimeSelfTest.Run();
    return;
}

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<WorkerHeartbeatStore>();
builder.Services.AddSingleton<WorkerState>();
builder.Services.AddSingleton<WorkerRegistry>();
builder.Services.AddSingleton<JobLeaseStore>();
builder.Services.AddHostedService<BrainSupervisorWorker>();
builder.Services.AddHostedService<VideoWorker>();
builder.Services.AddHostedService<MiningWorker>();
builder.Services.AddHostedService<QualityWorker>();
builder.Services.AddHostedService<SelfHealingWorker>();
builder.Services.AddHostedService<ResearchWorker>();
builder.Services.AddHostedService<ArchitectWorker>();
builder.Services.AddHostedService<EconomicWorker>();
builder.Services.AddHostedService<HealthWorker>();

var app = builder.Build();

// Liveness only: confirms the HTTP process is responsive. It does not claim
// that workers are ready, mining is active, or revenue has been realized.
app.MapGet("/healthz", () => Results.Ok(new
{
    status = "ok",
    service = "brain-cloud-worker"
}));

app.MapGet("/readyz", (WorkerState state) =>
{
    var requiredWorkers = new[]
    {
        "supervisor", "video", "mining", "quality", "self-healing",
        "research", "architect", "economic", "health"
    };
    var cutoff = DateTimeOffset.UtcNow.AddMinutes(-2);
    var latest = state.Snapshot()
        .GroupBy(p => p.WorkerId)
        .ToDictionary(g => g.Key, g => g.OrderByDescending(p => p.At).First());

    var checks = requiredWorkers.ToDictionary(
        id => id,
        id => latest.TryGetValue(id, out var pulse)
            && pulse.Status == "success"
            && pulse.At >= cutoff);

    var ready = checks.Values.All(passed => passed);
    return ready
        ? Results.Ok(new { ready = true, checks })
        : Results.Json(new { ready = false, checks }, statusCode: StatusCodes.Status503ServiceUnavailable);
});

app.MapGet("/health", (WorkerState state, WorkerRegistry registry) => Results.Ok(new
{
    ok = true,
    service = "brain-cloud-worker",
    state = "RUNNING",
    workers = registry.Snapshot(),
    recent_pulses = state.Snapshot().TakeLast(20)
}));

app.MapGet("/api/brain/status", (WorkerState state, WorkerRegistry registry) => Results.Ok(new
{
    ok = true,
    service = "brain-cloud-worker",
    workers = registry.Snapshot(),
    recent_pulses = state.Snapshot().TakeLast(50)
}));

app.MapPost("/api/brain/command", (HttpContext http, CommandRequest request) =>
{
    var expected = Environment.GetEnvironmentVariable("BRAIN_CLOUD_API_KEY");
    // Fail closed if deployment configuration omitted the API key.
    if (string.IsNullOrWhiteSpace(expected))
        return Results.Problem(
            statusCode: StatusCodes.Status503ServiceUnavailable,
            title: "COMMAND_AUTH_NOT_CONFIGURED",
            detail: "Command endpoint is disabled until BRAIN_CLOUD_API_KEY is configured.");

    if (!http.Request.Headers.TryGetValue("X-Brain-Api-Key", out var supplied) || supplied != expected)
        return Results.Unauthorized();

    var command = (request.Command ?? "").Trim();
    if (command.Length == 0 || command.Length > 4000)
        return Results.BadRequest(new { ok = false, error = "command must be 1..4000 characters" });

    // Do not claim a command was accepted: this endpoint is not yet connected
    // to the durable InternalTaskRuntime queue or a verified execution adapter.
    return Results.Problem(
        statusCode: StatusCodes.Status501NotImplemented,
        title: "COMMAND_EXECUTION_NOT_CONNECTED",
        detail: "Authentication succeeded, but no durable task queue is connected. No command was executed.");
});

app.Run();

public sealed record CommandRequest(string? Command);
