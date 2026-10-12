from __future__ import annotations
import argparse
import json
from pathlib import Path
from .engine import APMError, APMEngine, verify_evidence

def main() -> int:
    p = argparse.ArgumentParser(prog="python -m brain_v12.apm.cli")
    sub = p.add_subparsers(dest="action", required=True)
    for action in ("run", "resume"):
        x = sub.add_parser(action)
        x.add_argument("--pipeline", default=".brain/apm/pipeline.json")
        x.add_argument("--state-dir", default=".brain/apm/state")
    sub.add_parser("status").add_argument("--state-dir", default=".brain/apm/state")
    sub.add_parser("verify").add_argument("--state-dir", default=".brain/apm/state")
    args = p.parse_args()
    try:
        if args.action in {"run", "resume"}:
            result = APMEngine(Path(args.pipeline), Path(args.state_dir)).run(resume=args.action == "resume")
        elif args.action == "status":
            path = Path(args.state_dir) / "checkpoint.json"
            result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "NOT_STARTED"}
        else:
            result = verify_evidence(Path(args.state_dir))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") in {"PASS", "NOT_STARTED"} else 1
    except (APMError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}, ensure_ascii=False))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
