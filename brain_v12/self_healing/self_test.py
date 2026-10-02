#!/usr/bin/env python3
"""Dependency-free tests for the Brain self-healing core."""
from brain_v12.self_healing.supervisor import diagnose
from brain_v12.causal.causal_engine import self_test as causal_engine_test, causal_audit
from brain_v12.quran.quran_reasoning import self_test as quran_reasoning_test
from brain_v12.self_healing.reflection_agent import self_test as reflection_agent_test
from brain_v12.self_healing.reflection_actions import self_test as reflection_actions_test

def main() -> int:
    causal_engine_test()
    causal_audit()
    quran_reasoning_test()
    reflection_agent_test()
    reflection_actions_test()
    checks = [
        ("missing-token", diagnose("", "github_token_or_gh_token_required", 2)),
        ("syntax", diagnose("", "SyntaxError: invalid syntax", 1)),
        ("network", diagnose("", "Connection reset by peer", 1)),
        ("dependency", diagnose("", "ModuleNotFoundError: No module named x", 1)),
    ]
    failed = [name for name, result in checks if name not in result]
    if failed:
        print("SELF_TEST_FAILED", ",".join(failed))
        return 1
    print("CAUSAL_ENGINE=PASS")
    print("QURAN_REASONING_GUARD=PASS")
    print("REFLECTION_AGENT=PASS")
    print("REFLECTION_ACTIONS=PASS")
    print("SELF_TEST=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
