using System.Text.Json;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace BrainCloudWorker;

public sealed class BoundedTaskConsumer(DurableFileTaskQueue queue, ILogger<BoundedTaskConsumer> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var task = queue.TryLeaseNext("bounded-task-consumer", TimeSpan.FromMinutes(2));
                if (task is not null)
                {
                    var result = task.TaskType switch
                    {
                        "health_check" => JsonSerializer.Serialize(new { ok = true, task_type = task.TaskType, evidence_level = "LOCAL_QUEUE_CHECK_ONLY", external_runtime_verified = false }),
                        "simulation_status" => JsonSerializer.Serialize(new { ok = true, task_type = task.TaskType, mode = "SIMULATOR", network_access_performed = false, real_mining_verified = false, accepted_shares_verified = false, revenue_verified = false, evidence_level = "SIMULATION_STATUS_ONLY" }),
                        _ => throw new InvalidOperationException("TASK_TYPE_NOT_ALLOW_LISTED")
                    };
                    if (!queue.Complete(task.TaskId, task.LeaseId!, result))
                        logger.LogWarning("Task {TaskId} completion rejected because its lease expired.", task.TaskId);
                    continue;
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (Exception ex) { logger.LogError(ex, "Bounded task consumer iteration failed."); }
            await Task.Delay(TimeSpan.FromSeconds(1), stoppingToken);
        }
    }
}
