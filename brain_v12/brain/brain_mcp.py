from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP


def build_brain_mcp(brain_ai, device_bridge, store) -> FastMCP:
    """Build Electronic Brain's read-first MCP surface."""

    mcp = FastMCP(
        "Electronic Brain",
        stateless_http=True,
        json_response=True,
    )

    @mcp.tool()
    def brain_status() -> dict[str, Any]:
        """Return current BrainAI status and governed capabilities."""
        return {
            "ok": True,
            "source": "electronic-brain",
            "status": brain_ai.status(),
        }

    @mcp.tool()
    def brain_device_status() -> dict[str, Any]:
        """Return the latest status known for the configured Brain device bridge."""
        try:
            result = device_bridge.agent_status()
        except Exception as exc:
            return {
                "ok": False,
                "status": "DEVICE_STATUS_ERROR",
                "error": str(exc)[:500],
            }
        return {
            "ok": True,
            "source": "electronic-brain",
            "device": result,
        }

    @mcp.tool()
    def brain_evidence(limit: int = 10) -> dict[str, Any]:
        """Read recent Brain event evidence without mutating state."""
        limit = max(1, min(int(limit), 50))
        try:
            with store.connect() as con:
                rows = con.execute(
                    "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            events = [dict(row) for row in rows]
        except Exception as exc:
            return {
                "ok": False,
                "status": "EVIDENCE_READ_ERROR",
                "error": str(exc)[:500],
            }
        return {
            "ok": True,
            "source": "electronic-brain",
            "events": events,
            "count": len(events),
        }

    @mcp.tool()
    def brain_chat(message: str) -> dict[str, Any]:
        """Ask Brain through its governed BrainAI chat loop."""
        message = (message or "").strip()
        if not message:
            return {"ok": False, "status": "EMPTY_MESSAGE"}

        result = brain_ai.chat(message, approved=False)
        return {
            "ok": bool(result.ok),
            "status": result.mode,
            "reply": result.reply,
            "model": result.model,
            "tool_calls": result.tool_calls,
            "evidence": result.evidence,
            "error": result.error,
        }

    return mcp
