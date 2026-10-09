from pathlib import Path

from brain_v12.brain.windows_terraform_safety import inspect_windows_terraform_root


def test_repository_windows_terraform_root_is_safe() -> None:
    root = Path(__file__).resolve().parents[1] / "cloud" / "windows_terraform"
    assert root.is_dir(), "Windows Server 2025 Terraform root must exist in the repository"
    result = inspect_windows_terraform_root(root)
    assert result["safe"] is True, result["violations"]


def test_safe_root(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text(
        'source_address_prefix = var.allowed_source_ip\nadmin_password = var.admin_password\n',
        encoding="utf-8",
    )
    result = inspect_windows_terraform_root(tmp_path)
    assert result["safe"] is True


def test_rejects_open_network(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text(
        'source_address_prefix = "0.0.0.0/0"\n',
        encoding="utf-8",
    )
    result = inspect_windows_terraform_root(tmp_path)
    assert result["safe"] is False
    assert any("OPEN_NETWORK_RULE" in x for x in result["violations"])


def test_rejects_state_and_plan(tmp_path: Path) -> None:
    (tmp_path / "terraform.tfstate").write_text("{}", encoding="utf-8")
    (tmp_path / "brain.tfplan").write_bytes(b"opaque")
    result = inspect_windows_terraform_root(tmp_path)
    assert result["safe"] is False
    assert any("terraform.tfstate" in x for x in result["violations"])
    assert any("brain.tfplan" in x for x in result["violations"])


def test_allows_runtime_plan_artifact(tmp_path: Path) -> None:
    (tmp_path / "brain.tfplan").write_bytes(b"opaque")
    result = inspect_windows_terraform_root(tmp_path, allow_runtime_plan=True)
    assert result["safe"] is True


def test_rejects_inline_password(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text(
        'admin_password = "not-for-repo"\n',
        encoding="utf-8",
    )
    result = inspect_windows_terraform_root(tmp_path)
    assert result["safe"] is False
    assert any("INLINE_ADMIN_PASSWORD" in x for x in result["violations"])


def test_rejects_tfvars_files(tmp_path: Path) -> None:
    (tmp_path / "secrets.auto.tfvars").write_text(
        'admin_password = "not-for-repo"\n',
        encoding="utf-8",
    )
    result = inspect_windows_terraform_root(tmp_path)
    assert result["safe"] is False
    assert any("SENSITIVE_TFVARS_FILE" in x for x in result["violations"])
