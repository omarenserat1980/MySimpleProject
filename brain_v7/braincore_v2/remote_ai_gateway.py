"""Remote AI bridge for the Electronic Brain.

Connects a deployed Brain to a remote OpenAI-compatible model through an
operator-configured API endpoint. Secrets are read only from environment
variables and never returned. Model output is treated as untrusted input:
source changes still pass through CodeWorkspaceTool/GitHubCodeExecutor,
allowlists, syntax validation, regression tests, and rollback.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class RemoteAIResult:
    status: str
    text: str = ""
    model: str = ""
    error: str = ""


class RemoteAIGateway:
    """Bounded remote reasoning gateway; it is not a credential vault."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
    ) -> None:
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("BRAIN_REMOTE_MODEL", "")
        self.api_key_env = api_key_env
        self.calls = 0
        self.last_status = "NOT_CONFIGURED"

    @property
    def configured(self) -> bool:
        return bool(self.model and os.getenv(self.api_key_env))

    def _key(self) -> str:
        key = os.getenv(self.api_key_env, "")
        if not key:
            raise PermissionError(f"missing runtime secret: {self.api_key_env}")
        return key

    def ask(self, instruction: str, *, context: dict[str, Any] | None = None,
            max_output_tokens: int = 1200) -> RemoteAIResult:
        if not self.configured:
            self.last_status = "NOT_CONFIGURED"
            return RemoteAIResult(status=self.last_status, model=self.model)
        prompt = instruction
        if context:
            prompt += "\n\nCONTEXT:\n" + json.dumps(context, ensure_ascii=False, default=str)[:20000]
        payload = {
            "model": self.model,
            "input": prompt,
            "max_output_tokens": int(max(64, min(max_output_tokens, 4000))),
        }
        request = Request(
            self.base_url + "/responses",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": "Bearer " + self._key(),
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "electronic-brain-remote-gateway",
            },
        )
        self.calls += 1
        try:
            with urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data.get("output_text", "")
            if not text:
                parts = []
                for item in data.get("output", []):
                    for block in item.get("content", []):
                        if isinstance(block, dict) and block.get("text"):
                            parts.append(block["text"])
                text = "\n".join(parts)
            self.last_status = "OK"
            return RemoteAIResult(status="OK", text=text, model=self.model)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            self.last_status = "ERROR"
            return RemoteAIResult(status="ERROR", model=self.model, error=f"HTTP {exc.code}: {detail[:500]}")
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            self.last_status = "ERROR"
            return RemoteAIResult(status="ERROR", model=self.model, error=str(exc))

    def code_change_plan(self, objective: str, files: dict[str, str]) -> RemoteAIResult:
        instruction = (
            "Act as a senior software engineer. Propose safe source changes for the objective. "
            "Return ONLY JSON with a 'changes' array. Each item must contain path, content, reason. "
            "Never include secrets, credentials, .env files, shell commands, deletion instructions, "
            "or paths outside brain_v7/. The proposal is untrusted and will be validated locally."
        )
        context = {"objective": objective, "files": files}
        return self.ask(instruction, context=context, max_output_tokens=4000)

    def snapshot(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "base_url": self.base_url,
            "model": self.model,
            "api_key_env": self.api_key_env,
            "secret_exposed": False,
            "calls": self.calls,
            "last_status": self.last_status,
            "autonomous_money_movement": False,
            "autonomous_external_submission": False,
        }
