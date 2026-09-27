using System.Diagnostics;
using System.Text.Json;

namespace Brain6;

public sealed record Checkpoint(int Attempt, string Status, DateTimeOffset Timestamp);

public sealed class Supervisor
{
    private readonly string _cppPath;
    private readonly string _checkpointPath = "brain6_cs/checkpoint.json";

    public Supervisor(string cppPath) => _cppPath = cppPath;

    public async Task<int> RunAsync(CancellationToken cancellationToken)
    {
        Console.WriteLine("BRAIN6_CSHARP_BOOT version=1 mode=CPP_BRIDGE");

        if (!File.Exists("production/BRAIN6_168H.json"))
        {
            Console.Error.WriteLine("BRAIN6_STATE_MISSING");
            return 20;
        }

        var retries = ReadPositiveInt("BRAIN6_CS_RETRIES", 2);
        for (var attempt = 1; attempt <= retries + 1; attempt++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            Console.WriteLine($"BRAIN6_CS_ATTEMPT {attempt}");

            var exitCode = await RunCppAsync(cancellationToken);
            if (exitCode == 0 && await VerifyFinalMediaAsync(cancellationToken))
            {
                await SaveCheckpointAsync(new(attempt, "SUCCESS", DateTimeOffset.UtcNow));
                Console.WriteLine("BRAIN6_CS_FINAL_QC_OK");
                return 0;
            }

            await SaveCheckpointAsync(new(attempt, "RETRY", DateTimeOffset.UtcNow));
            if (attempt <= retries)
                await Task.Delay(TimeSpan.FromSeconds(ReadPositiveInt("BRAIN6_CS_BACKOFF_SECONDS", 5)), cancellationToken);
        }

        await SaveCheckpointAsync(new(retries + 1, "FAILED", DateTimeOffset.UtcNow));
        Console.Error.WriteLine("BRAIN6_CS_FINAL_QC_FAILED");
        return 2;
    }

    private async Task<int> RunCppAsync(CancellationToken token)
    {
        var psi = new ProcessStartInfo
        {
            FileName = _cppPath,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false
        };

        using var process = new Process { StartInfo = psi };
        process.OutputDataReceived += (_, e) => { if (e.Data is not null) Console.WriteLine(e.Data); };
        process.ErrorDataReceived += (_, e) => { if (e.Data is not null) Console.Error.WriteLine(e.Data); };

        if (!process.Start()) return 127;
        process.BeginOutputReadLine();
        process.BeginErrorReadLine();

        await process.WaitForExitAsync(token);
        return process.ExitCode;
    }

    private static async Task<bool> VerifyFinalMediaAsync(CancellationToken token)
    {
        var output = Path.Combine("cinematic_output", "final.mp4");
        if (!File.Exists(output) || new FileInfo(output).Length == 0) return false;

        var psi = new ProcessStartInfo
        {
            FileName = "ffprobe",
            Arguments = "-v error -show_entries stream=codec_type -of csv=p=0 cinematic_output/final.mp4",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false
        };

        using var process = Process.Start(psi);
        if (process is null) return false;

        var stdout = await process.StandardOutput.ReadToEndAsync(token);
        await process.WaitForExitAsync(token);

        var hasVideo = stdout.Split('\n', StringSplitOptions.RemoveEmptyEntries).Any(x => x.Trim() == "video");
        var hasAudio = stdout.Split('\n', StringSplitOptions.RemoveEmptyEntries).Any(x => x.Trim() == "audio");
        return process.ExitCode == 0 && hasVideo && hasAudio;
    }

    private async Task SaveCheckpointAsync(Checkpoint checkpoint)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_checkpointPath)!);
        await File.WriteAllTextAsync(
            _checkpointPath,
            JsonSerializer.Serialize(checkpoint, new JsonSerializerOptions { WriteIndented = true }));
    }

    private static int ReadPositiveInt(string name, int fallback)
    {
        var value = Environment.GetEnvironmentVariable(name);
        return int.TryParse(value, out var parsed) && parsed > 0 ? parsed : fallback;
    }
}

public static class Program
{
    public static async Task<int> Main()
    {
        using var cts = new CancellationTokenSource();
        Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };

        var cpp = Environment.GetEnvironmentVariable("BRAIN6_CPP_BINARY") ?? "brain6_cpp/brain6";
        return await new Supervisor(cpp).RunAsync(cts.Token);
    }
}
