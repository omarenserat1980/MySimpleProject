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

// Liveness confirms only that the HTTP process responds. It does not claim
// workers are ready, mining is active, or revenue has been realized.
app.MapGet("/healthz", () => Results.Ok(new
{
    status = "ok",
    service = "brain-cloud-worker"
}));

app.MapGet("/readyz", (WorkerState state) =>
{
    var result = WorkerReadinessPolicy.Evaluate(
        state.Snapshot(),
        DateTimeOffset.UtcNow,
        TimeSpan.FromMinutes(2));

    return result.Ready
        ? Results.Ok(new { ready = true, checks = result.Checks })
        : Results.Json(new { ready = false, checks = result.Checks },
            statusCode: StatusCodes.Status503ServiceUnavailable);
});

app.MapGet("/health", (WorkerState state, WorkerRegistry registry) => Results.Ok(new
{
    ok = true,
    service = "brain-cloud-worker",
    state = "RUNNING",
    workers = registry.SnapshotWithFreshness(DateTimeOffset.UtcNow, TimeSpan.FromMinutes(2)),
    recent_pulses = state.Snapshot().TakeLast(20)
}));

app.MapGet("/api/brain/status", (WorkerState state, WorkerRegistry registry) => Results.Ok(new
{
    ok = true,
    service = "brain-cloud-worker",
    workers = registry.SnapshotWithFreshness(DateTimeOffset.UtcNow, TimeSpan.FromMinutes(2)),
    recent_pulses = state.Snapshot().TakeLast(50)
}));

app.MapPost("/api/brain/command", (HttpContext http, CommandRequest request) =>
{
    var expected = Environment.GetEnvironmentVariable("BRAIN_CLOUD_API_KEY");
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

    return Results.Problem(
        statusCode: StatusCodes.Status501NotImplemented,
        title: "COMMAND_EXECUTION_NOT_CONNECTED",
        detail: "Authentication succeeded, but no durable task queue is connected. No command was executed.");
});

app.Run();

public sealed record CommandRequest(string? Command);
