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

app.MapPost("/api/brain/command", async (HttpContext http, CommandRequest request, WorkerState state) =>
{
    var expected = Environment.GetEnvironmentVariable("BRAIN_CLOUD_API_KEY");
    if (!string.IsNullOrWhiteSpace(expected))
    {
        if (!http.Request.Headers.TryGetValue("X-Brain-Api-Key", out var supplied) || supplied != expected)
            return Results.Unauthorized();
    }

    var command = (request.Command ?? "").Trim();
    if (command.Length == 0 || command.Length > 4000)
        return Results.BadRequest(new { ok = false, error = "command must be 1..4000 characters" });

    var id = Guid.NewGuid().ToString("N");
    state.Record("api", "accepted", $"command_id={id}");
    await Task.CompletedTask;

    return Results.Accepted($"/api/brain/command/{id}", new
    {
        ok = true,
        command_id = id,
        state = "ACCEPTED",
        command
    });
});

app.Run();

public sealed record CommandRequest(string? Command);
