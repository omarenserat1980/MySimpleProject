"""One-hour continuous dialogue/development session engine.

This schedules a bounded 60-minute session inside the external worker.
It does not create a hidden ChatGPT conversation or run after the worker
process stops. Each turn is recorded locally and can feed the next objective.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import time
from typing import Callable, Optional


SESSION_SECONDS = 60 * 60


@dataclass(frozen=True)
class DialogueTurn:
    turn: int
    speaker: str
    message: str
    timestamp: float
    development_action: str = ""


@dataclass
class HourSession:
    session_id: str
    started_at: float
    duration_seconds: int = SESSION_SECONDS
    turns: list[DialogueTurn] | None = None
    status: str = "RUNNING"

    def __post_init__(self) -> None:
        if self.turns is None:
            self.turns = []

    @property
    def elapsed_seconds(self) -> float:
        return max(0.0, time.time() - self.started_at)

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.duration_seconds - self.elapsed_seconds)

    @property
    def finished(self) -> bool:
        return self.elapsed_seconds >= self.duration_seconds or self.status != "RUNNING"

    def add_turn(self, speaker: str, message: str, development_action: str = "") -> DialogueTurn:
        if self.finished:
            self.status = "FINISHED"
            raise RuntimeError("hour session finished")
        turn = DialogueTurn(
            turn=len(self.turns or []) + 1,
            speaker=str(speaker),
            message=str(message),
            timestamp=time.time(),
            development_action=str(development_action),
        )
        self.turns.append(turn)
        return turn

    def finish(self, reason: str = "TIME_LIMIT") -> None:
        self.status = "FINISHED"
        self.add_turn("system", reason) if not self.finished else None

    def snapshot(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "started_at": self.started_at,
            "duration_seconds": self.duration_seconds,
            "elapsed_seconds": self.elapsed_seconds,
            "remaining_seconds": self.remaining_seconds,
            "turn_count": len(self.turns or []),
            "turns": [asdict(t) for t in (self.turns or [])],
        }


def create_session(session_id: Optional[str] = None, now: Optional[float] = None) -> HourSession:
    started = time.time() if now is None else float(now)
    sid = session_id or f"hour-{int(started)}"
    return HourSession(session_id=sid, started_at=started)


def run_turn_loop(
    session: HourSession,
    turn_fn: Callable[[HourSession], tuple[str, str, str]],
    *,
    max_turns: int = 600,
    sleep_seconds: float = 1.0,
) -> dict:
    """Run dialogue/development turns until 60 minutes or the safety bound.

    turn_fn returns (speaker, message, development_action).
    The caller supplies the actual model/agent bridge; this module only
    orchestrates and records the session.
    """
    max_turns = max(1, int(max_turns))
    while not session.finished and len(session.turns or []) < max_turns:
        speaker, message, action = turn_fn(session)
        session.add_turn(speaker, message, action)
        if session.finished:
            break
        if sleep_seconds > 0:
            time.sleep(min(float(sleep_seconds), session.remaining_seconds))
    if not session.finished:
        session.finish("TURN_LIMIT")
    return session.snapshot()
