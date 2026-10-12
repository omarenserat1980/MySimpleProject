"""Autonomous film production supervisor with evidence-gated completion.

The supervisor may report success only after FFprobe verifies a non-empty
audio/video artifact and the Brain evidence store verifies the runtime record.
It never publishes externally.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .brain_supervisor import BrainSupervisor


class FilmSupervisor:
    def __init__(self, work="/tmp/last-light", artifact_root="brain6_artifacts", max_attempts=3):
        self.work = Path(work)
        self.artifacts = Path(artifact_root)
        self.max_attempts = max(1, min(int(max_attempts), 3))
        self.artifacts.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _blocked(job):
        return job.get("phase") == "blocked" or job.get("status") == "blocked"

    def _start_lifecycle(self, supervisor, job):
        for phase in ("discover", "plan", "select_backend"):
            job = supervisor.transition(job, phase, details={"source": "film_supervisor"})
            if self._blocked(job):
                return job
        return job

    def _retry_lifecycle(self, supervisor, job, details):
        job = supervisor.transition(job, "repair", details={"action": "rebuild_artifact", **details})
        if self._blocked(job):
            return job
        job = supervisor.transition(job, "recover", details={"bounded_retry": True})
        if self._blocked(job):
            return job
        return supervisor.transition(job, "retry", details={"bounded_retry": True})

    def run(self, seconds=12, fps=12):
        self.work.mkdir(parents=True, exist_ok=True)
        supervisor = BrainSupervisor(str(self.artifacts / "supervisor"), self.max_attempts)
        job = supervisor.create("film:last-light", budget=self.max_attempts + 2)
        job = self._start_lifecycle(supervisor, job)
        trace = []

        if self._blocked(job):
            trace.append({"phase": "blocked", "details": job.get("details", {})})
            supervisor.snapshot(job, {"verified": False, "trace": trace})
            (self.artifacts / "film_supervisor_trace.json").write_text(
                json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return 1

        for attempt in range(1, self.max_attempts + 1):
            trace.append({"attempt": attempt, "phase": "discover", "ok": True})
            trace.append({"attempt": attempt, "phase": "plan", "backend": "local_python_ffmpeg_renderer"})
            job = supervisor.transition(job, "execute", details={"attempt": attempt, "backend": "local_python_ffmpeg_renderer"})
            if self._blocked(job) or job.get("phase") != "execute":
                trace.append({"attempt": attempt, "phase": "execute", "ok": False, "reason": job.get("details", {})})
                supervisor.snapshot(job, {"verified": False, "trace": trace})
                (self.artifacts / "film_supervisor_trace.json").write_text(
                    json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                return 1

            try:
                out = subprocess.run(
                    ["python", "cloud/last_light_movie.py", "--output", str(self.work),
                     "--seconds", str(seconds), "--fps", str(fps)],
                    text=True, capture_output=True, check=False,
                )
            except OSError as exc:
                out = None
                execution_error = str(exc)
            else:
                execution_error = out.stderr[-2000:] if out.returncode != 0 else ""

            if out is None or out.returncode != 0:
                failure = {"reason": "renderer_execution_failed", "stderr": execution_error}
                trace.append({"attempt": attempt, "phase": "execute", "ok": False, **failure})
                supervisor.observe(job["job_id"], "film_attempt_failed", failure, source="film_supervisor")
                job = supervisor.transition(job, "verify", details=failure)
                if attempt < self.max_attempts:
                    job = self._retry_lifecycle(supervisor, job, failure)
                    if self._blocked(job):
                        break
                    shutil.rmtree(self.work, ignore_errors=True)
                    self.work.mkdir(parents=True, exist_ok=True)
                    continue
                break

            ok, details = self.verify()
            trace.append({"attempt": attempt, "phase": "verify", "ok": ok, "details": details})
            if ok:
                manifest = {
                    "title": "آخر ضوء في المدينة",
                    "status": "VERIFIED_COMPLETED",
                    "renderer": "Python/Pillow + FFmpeg",
                    "control_plane": "brain_supervisor",
                    "attempts": attempt,
                    "verified": True,
                    "verification": details,
                }
                (self.work / "film_manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                (self.work / "VERIFIED_COMPLETED").write_text("verified\n", encoding="utf-8")

                # This is runtime evidence produced only after the independent media probe passed.
                supervisor.observe(
                    job["job_id"], "film_artifact_verified",
                    {"artifact": str(self.work / "last_light_city.mp4"),
                     "size_bytes": (self.work / "last_light_city.mp4").stat().st_size,
                     "ffprobe": details, "manifest_status": manifest["status"]},
                    source="film_supervisor", confidence=1.0,
                )
                job = supervisor.transition(
                    job, "verify", details={"artifact_verified": True, "attempt": attempt}
                )
                if self._blocked(job):
                    break
                job = supervisor.transition(
                    job, "deliver", status="completed",
                    details={"attempts": attempt, "evidence_kind": "film_artifact_verified"},
                    required_evidence_kind="film_artifact_verified",
                )
                if job.get("status") == "completed" and job.get("phase") == "deliver":
                    supervisor.snapshot(job, {"verified": True, "attempts": attempt, "trace": trace})
                    (self.artifacts / "film_supervisor_trace.json").write_text(
                        json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    return 0

                trace.append({"attempt": attempt, "phase": "deliver", "ok": False, "details": job.get("details", {})})
                break

            # A failed probe is recorded as a failure, never as success evidence.
            supervisor.observe(job["job_id"], "film_artifact_check_failed", details, source="film_supervisor")
            job = supervisor.transition(job, "verify", details=details)
            if attempt < self.max_attempts:
                job = self._retry_lifecycle(supervisor, job, details)
                if self._blocked(job):
                    break
                (self.work / "last_light_city.mp4").unlink(missing_ok=True)
                (self.work / "ffprobe.json").unlink(missing_ok=True)

        trace.append({"phase": "failed", "attempts": self.max_attempts})
        if job.get("status") != "blocked":
            job = supervisor.transition(
                job, "blocked", status="blocked",
                details={"reason": "film_verification_or_execution_failed", "attempts": self.max_attempts},
            )
        supervisor.snapshot(job, {"verified": False, "trace": trace})
        (self.artifacts / "film_supervisor_trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return 1

    def verify(self):
        mp4 = self.work / "last_light_city.mp4"
        if not mp4.exists() or mp4.stat().st_size <= 0:
            return False, {"reason": "missing_or_empty_mp4"}
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
             "-show_entries", "stream=codec_type,codec_name,width,height", "-of", "json", str(mp4)],
            text=True, capture_output=True, check=False,
        )
        if probe.returncode != 0:
            return False, {"reason": "ffprobe_failed", "stderr": probe.stderr[-1000:]}
        try:
            data = json.loads(probe.stdout)
        except (TypeError, json.JSONDecodeError):
            return False, {"reason": "ffprobe_invalid_json", "stdout": probe.stdout[-1000:]}
        streams = data.get("streams", [])
        fmt = data.get("format", {})
        ok = (
            any(s.get("codec_type") == "video" for s in streams)
            and any(s.get("codec_type") == "audio" for s in streams)
            and float(fmt.get("duration", 0) or 0) > 0
            and int(fmt.get("size", 0) or 0) > 0
        )
        (self.work / "ffprobe.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        return ok, {"streams": streams, "format": fmt}


if __name__ == "__main__":
    raise SystemExit(FilmSupervisor().run())
