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
builder.Services.AddSingleton<DurableFileTaskQueue>(services =>
{
    var path = Environment.GetEnvironmentVariable("BRAIN_TASK_QUEUE_PATH");
    if (string.IsNullOrWhiteSpace(path))
        path = "/var/lib/brain/task-queue.json";
    return new DurableFileTaskQueue(path);
});
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

app.MapGet("/readyz", (WorkerState state, WorkerRegistry registry) =>
{
    var now = DateTimeOffset.UtcNow;
    var maxAge = TimeSpan.FromMinutes(2);
    var result = WorkerReadinessPolicy.Evaluate(
        state.Snapshot(),
        registry.SnapshotWithFreshness(now, maxAge),
        now,
        maxAge);

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

// Bounded task API: it only queues allow-listed task types. It does not execute them.
app.MapPost("/api/tasks", (HttpContext http, TaskSubmissionRequest request, DurableFileTaskQueue queue) =>
{
    if (!IsAuthorized(http))
        return Results.Unauthorized();

    if (!http.Request.Headers.TryGetValue("Idempotency-Key", out var idempotencyKey) ||
        string.IsNullOrWhiteSpace(idempotencyKey))
        return Results.BadRequest(new { ok = false, error = "IDEMPOTENCY_KEY_REQUIRED" });

    if (request.Arguments.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null)
        return Results.BadRequest(new { ok = false, error = "TASK_ARGUMENTS_REQUIRED" });

    try
    {
        var result = queue.Submit(
            "cloud-api-key",
            idempotencyKey.ToString(),
            request.TaskType ?? "",
            request.Arguments.GetRawText());
        var task = result.Task;
        return Results.Json(new
        {
            ok = true,
            duplicate = result.Duplicate,
            task = new { task.TaskId, task.TaskType, task.Status, task.CreatedAt, task.UpdatedAt, task.Attempt }
        }, statusCode: result.Duplicate ? StatusCodes.Status200OK : StatusCodes.Status202Accepted);
    }
    catch (InvalidOperationException ex) when (ex.Message == "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT")
    {
        return Results.Conflict(new { ok = false, error = "IDEMPOTENCY_KEY_PAYLOAD_CONFLICT" });
    }
    catch (ArgumentException)
    {
        return Results.BadRequest(new { ok = false, error = "INVALID_TASK_REQUEST", allowedTaskTypes = new[] { "health_check", "simulation_status" } });
    }
});

app.MapGet("/api/tasks/{taskId}", (HttpContext http, string taskId, DurableFileTaskQueue queue) =>
{
    if (!IsAuthorized(http))
        return Results.Unauthorized();

    var task = queue.Snapshot().FirstOrDefault(t => t.TaskId == taskId);
    if (task is null) return Results.NotFound(new { ok = false, error = "TASK_NOT_FOUND" });

    return Results.Ok(new
    {
        ok = true,
        task = new { task.TaskId, task.TaskType, task.Status, task.CreatedAt, task.UpdatedAt, task.Attempt, task.ResultJson, task.ErrorCode }
    });
});

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

static bool IsAuthorized(HttpContext http)
{
    var expected = Environment.GetEnvironmentVariable("BRAIN_CLOUD_API_KEY");
    return !string.IsNullOrWhiteSpace(expected) &&
        http.Request.Headers.TryGetValue("X-Brain-Api-Key", out var supplied) &&
        supplied == expected;
}

public sealed record TaskSubmissionRequest(string? TaskType, System.Text.Json.JsonElement Arguments);
public sealed record CommandRequest(string? Command);
