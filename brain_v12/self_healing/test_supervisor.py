from brain_v12.self_healing.supervisor import diagnose


def test_diagnose_missing_token():
    assert "missing-token" in diagnose("", "GITHUB_TOKEN_REQUIRED", 2)


def test_diagnose_syntax():
    assert "syntax" in diagnose("", "SyntaxError: invalid syntax", 1)


def test_diagnose_network():
    assert "network" in diagnose("", "Connection reset by peer", 1)


def test_workflow_actions_disabled_by_default(monkeypatch):
    monkeypatch.delenv("BRAIN_ENABLE_WORKFLOW_ACTIONS", raising=False)
    from brain_v12.self_healing.supervisor import workflow_actions_enabled
    assert workflow_actions_enabled() is False


def test_workflow_actions_require_explicit_opt_in():
    from brain_v12.self_healing.supervisor import workflow_actions_enabled
    assert workflow_actions_enabled("1") is True
    assert workflow_actions_enabled("true") is True
    assert workflow_actions_enabled("yes") is True
    assert workflow_actions_enabled("0") is False
    assert workflow_actions_enabled("false") is False
    assert workflow_actions_enabled("anything") is False


def test_workflow_actions_environment_value_is_normalized(monkeypatch):
    from brain_v12.self_healing.supervisor import workflow_actions_enabled

    monkeypatch.setenv("BRAIN_ENABLE_WORKFLOW_ACTIONS", " TRUE ")
    assert workflow_actions_enabled() is True

    monkeypatch.setenv("BRAIN_ENABLE_WORKFLOW_ACTIONS", " YES ")
    assert workflow_actions_enabled() is True

    monkeypatch.setenv("BRAIN_ENABLE_WORKFLOW_ACTIONS", "on")
    assert workflow_actions_enabled() is False



def test_workflow_action_is_not_registered_when_disabled(monkeypatch):
    from brain_v12.self_healing.reflection_actions import ReflectionActionRegistry
    from brain_v12.self_healing.supervisor import register_workflow_action

    monkeypatch.delenv("BRAIN_ENABLE_WORKFLOW_ACTIONS", raising=False)
    registry = ReflectionActionRegistry()

    assert register_workflow_action(registry) is False
    assert "workflow:reflection-e2e" not in registry.ids()


def test_workflow_action_registration_is_fixed_and_allowlisted(monkeypatch):
    from brain_v12.self_healing import supervisor
    from brain_v12.self_healing.reflection_actions import ActionResult, ReflectionActionRegistry

    captured = {}

    def fake_dispatch(action_id, **kwargs):
        captured["action_id"] = action_id
        captured.update(kwargs)
        return lambda: ActionResult(action_id, True, 0, "not executed", "")

    monkeypatch.delenv("BRAIN_GITHUB_REPO", raising=False)
    monkeypatch.delenv("BRAIN_GITHUB_REF", raising=False)
    monkeypatch.setattr(
        "brain_v12.self_healing.reflection_actions.workflow_dispatch_action",
        fake_dispatch,
    )
    registry = ReflectionActionRegistry()

    assert supervisor.register_workflow_action(registry, enabled=True) is True
    assert registry.ids() == ["workflow:reflection-e2e"]
    assert captured["workflow_id"] == "reflection-e2e"
    assert captured["repo"] == "omarenserat1980/MySimpleProject"
    assert captured["ref"] == "main"



def test_existing_supervisor_lock_is_not_overwritten_and_target_does_not_run(tmp_path):
    target = tmp_path / "target.py"
    marker = tmp_path / "target-ran.txt"
    target.write_text(
        "from pathlib import Path\\n"
        + "Path(" + repr(str(marker)) + ").write_text('ran', encoding='utf-8')\\n",
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    lock_path = state_dir / "supervisor.lock"
    original_lock = "existing-owner 2026-01-01T00:00:00+00:00\\n"
    lock_path.write_text(original_lock, encoding="utf-8")

    env = os.environ.copy()
    env["BRAIN_CHATGPT_REFLECTION"] = "0"
    env.pop("BRAIN_ENABLE_WORKFLOW_ACTIONS", None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "brain_v12.self_healing.supervisor",
            "--command", _command(target),
            "--state", str(state_dir),
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 3
    assert "BRAIN_SUPERVISOR_ALREADY_RUNNING" in result.stdout
    assert lock_path.read_text(encoding="utf-8") == original_lock
    assert not marker.exists()
