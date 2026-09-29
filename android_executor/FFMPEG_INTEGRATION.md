# Real FFmpeg + Queue/Resume

The Android Executor now contains a real FFmpeg process adapter and a durable queue.

## Binary

Place a device-compatible executable at:
data/data/com.electronicbrain.androidexecutor/files/bin/ffmpeg

The release should package the binary explicitly. The app does not download executable code at runtime.

## Queue

State is persisted in app-private executor-queue.json.

PENDING -> RUNNING -> SUCCEEDED/FAILED -> VERIFIED

On restart, RUNNING items are returned to PENDING so unfinished work can resume.

Example:
{
  "task": "ffmpeg_run",
  "args": {
    "argv": ["-y","-i","/storage/emulated/0/Movies/ElectronicBrain/input.mp4","-c:v","copy","/storage/emulated/0/Movies/ElectronicBrain/output.mp4"]
  }
}

Process exit 0 is execution success, not VERIFIED. Verification is separate.
