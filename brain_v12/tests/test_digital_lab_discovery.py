from pathlib import Path

from brain_v12.digital_lab.discover_assets import build_inventory, classify

def test_classify_common_brain_assets():
    assert classify(Path(".github/workflows/ci.yml")) == "workflow"
    assert classify(Path("brain_v12/asic/core.sv")) == "asic_rtl"
    assert classify(Path("asic/core.v")) == "asic_rtl"
    assert classify(Path("brain_v12/tools/repair.py")) == "code_or_script"
    assert classify(Path("infra/main.tf")) == "infrastructure"
    assert classify(Path("README.md")) == "documentation"

def test_inventory_is_metadata_only_and_explicit_about_limits(tmp_path):
    (tmp_path / "main.py").write_text("print(1)", encoding="utf-8")
    (tmp_path / ".env").write_text("DO_NOT_READ=secret", encoding="utf-8")
    (tmp_path / "brain-digital-lab-inventory.json").write_text("old report", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "ignored.txt").write_text("ignored", encoding="utf-8")

    report = build_inventory(tmp_path)

    assert report["asset_count"] == 2
    assert {asset["path"] for asset in report["assets"]} == {"main.py", ".env"}
    assert all(asset["verification_status"] == "NOT_RUN" for asset in report["assets"])
    assert any("does not prove runtime health" in limitation
               for limitation in report["coverage_limitations"])
    assert "secret" not in str(report)

def test_inventory_does_not_follow_symlinks(tmp_path):
    target = tmp_path / "real.txt"
    target.write_text("content", encoding="utf-8")
    link = tmp_path / "linked.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        return
    report = build_inventory(tmp_path)
    assert [asset["path"] for asset in report["assets"]] == ["real.txt"]