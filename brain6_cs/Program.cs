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
        Console.WriteLine("BRAIN6_CSHARP_BOOT version=2 mode=CPP_BRIDGE_TIMEOUT");

        if (!File.Exists("production/BRAIN6_168H.json"))
        {
            Console.Error.WriteLine("BRAIN6_STATE_MISSING");
            return 20;
        }

        var retries = ReadNonNegativeInt("BRAIN6_CS_RETRIES", 0);
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

            await SaveCheckpointAsync(new(attempt, exitCode == 124 ? "TIMEOUT" : "RETRY", DateTimeOffset.UtcNow));
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

        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(token);
        timeoutCts.CancelAfter(TimeSpan.FromSeconds(ReadPositiveInt("BRAIN6_EXECUTION_TIMEOUT_SECONDS", 19800)));

        try
        {
            await process.WaitForExitAsync(timeoutCts.Token);
        }
        catch (OperationCanceledException) when (!token.IsCancellationRequested)
        {
            Console.Error.WriteLine("BRAIN6_CS_CPP_TIMEOUT");
            try { process.Kill(entireProcessTree: true); } catch { }
            await process.WaitForExitAsync(CancellationToken.None);
            return 124;
        }

        return process.ExitCode;
    }

    private static async Task<bool> VerifyFinalMediaAsync(CancellationToken token)
    {
        var output = Path.Combine("cinematic_output", "final.mp4");
        if (!File.Exists(output) || new FileInfo(output).Length == 0) return false;

        var psi = new ProcessStartInfo
        {
            FileName = "ffprobe",
            Arguments = "-v error -show_entries format=duration:stream=codec_type,width,height -of json cinematic_output/final.mp4",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false
        };

        using var process = Process.Start(psi);
        if (process is null) return false;

        var stdout = await process.StandardOutput.ReadToEndAsync(token);
        var stderr = await process.StandardError.ReadToEndAsync(token);
        await process.WaitForExitAsync(token);
        if (process.ExitCode != 0) return false;

        try
        {
            using var doc = JsonDocument.Parse(stdout);
            var duration = doc.RootElement.GetProperty("format").GetProperty("duration").GetDouble();
            var streams = doc.RootElement.GetProperty("streams");
            var hasVideo = false;
            var hasAudio = false;
            var validVideo = false;

            foreach (var stream in streams.EnumerateArray())
            {
                var type = stream.GetProperty("codec_type").GetString();
                if (type == "audio") hasAudio = true;
                if (type == "video")
                {
                    hasVideo = true;
                    var width = stream.TryGetProperty("width", out var w) ? w.GetInt32() : 0;
                    var height = stream.TryGetProperty("height", out var h) ? h.GetInt32() : 0;
                    validVideo = width >= 640 && height >= 360;
                }
            }

            return duration >= 1 && hasVideo && hasAudio && validVideo;
        }
        catch (JsonException)
        {
            Console.Error.WriteLine(stderr);
            return false;
        }
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

    private static int ReadNonNegativeInt(string name, int fallback)
    {
        var value = Environment.GetEnvironmentVariable(name);
        return int.TryParse(value, out var parsed) && parsed >= 0 ? parsed : fallback;
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