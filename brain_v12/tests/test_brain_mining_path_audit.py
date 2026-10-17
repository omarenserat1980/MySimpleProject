from pathlib import Path

from brain_v12.tools.brain_mining_path_audit import audit


def test_audit_distinguishes_shared_prefix_from_duplicate_route(tmp_path: Path):
    (tmp_path / "brain_v12" / "brain").mkdir(parents=True)
    (tmp_path / "brain_v12" / "tools").mkdir(parents=True)
    (tmp_path / "brain_v12" / "brain" / "mining_api.py").write_text(
        "router = APIRouter(prefix='/api/mining-node')\n"
        "@router.get('/status')\ndef status(): return {}\n"
        "TOKEN = os.getenv('BRAIINS_POOL_API_TOKEN')\n",
        encoding="utf-8",
    )
    (tmp_path / "brain_v12" / "brain" / "digital_mining_api.py").write_text(
        "router = APIRouter(prefix='/api/mining-node')\n"
        "@router.get('/local-preflight')\ndef preflight(): return {}\n",
        encoding="utf-8",
    )
    (tmp_path / "brain_v12" / "brain" / "stratum_v1_offline_simulator.py").write_text(
        "# simulated only\n",
        encoding="utf-8",
    )
    (tmp_path / "brain_v12" / "tools" / "braiins_pool_readonly_diagnostics.py").write_text(
        "API = 'https://example.invalid'\n",
        encoding="utf-8",
    )
    (tmp_path / ".brain_env").write_text(
        "BRAIINS_POOL_API_TOKEN=DO_NOT_READ_OR_PRINT\n",
        encoding="utf-8",
    )

    result = audit(tmp_path)

    assert result["mode"] == "READ_ONLY_STATIC"
    assert "/api/mining-node" in result["shared_static_api_router_prefixes"]
    assert result["duplicate_static_api_routes"] == {}
    assert result["configuration_reference_locations"]["BRAIINS_POOL_API_TOKEN"]
    assert result["secrets_values_printed"] is False
    assert result["network_accessed"] is False
    assert result["miner_started"] is False
    assert "DO_NOT_READ_OR_PRINT" not in str(result)


def test_audit_flags_exact_method_path_duplicates(tmp_path: Path):
    (tmp_path / "brain_v12").mkdir()
    for name in ("first_api.py", "second_api.py"):
        (tmp_path / "brain_v12" / name).write_text(
            "router = APIRouter(prefix='/api/mining-node')\n"
            "@router.get('/status')\ndef status(): return {}\n",
            encoding="utf-8",
        )
    result = audit(tmp_path)
    assert result["duplicate_static_api_routes"]["GET /api/mining-node/status"]


def test_audit_handles_missing_git_and_empty_root(tmp_path: Path):
    result = audit(tmp_path)
    assert result["audit"] == "brain-mining-path-audit"
    assert result["git"]["branch"] is None
    assert result["git"]["commit"] is None
    assert result["files_modified"] is False
    assert result["real_mining_verified"] is False
