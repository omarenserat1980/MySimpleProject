using BrainCloudWorker;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

if (args.Contains("--self-test", StringComparer.OrdinalIgnoreCase))
{
    WorkerRuntimeSelfTest.Run();
    return;
}

var builder = Host.CreateApplicationBuilder(args);
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
await builder.Build().RunAsync();