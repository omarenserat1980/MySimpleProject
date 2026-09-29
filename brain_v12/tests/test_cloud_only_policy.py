from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cloud_runtime_is_device_independent():
    source = (ROOT / "cloud" / "brain_cloud.py").read_text(encoding="utf-8")
    assert "BRAIN_CLOUD_DEVICE_REQUIRED=0" in source
    assert "BRAIN_CLOUD_TERMUX_REQUIRED=0" in source


def test_external_termux_deploy_assets_are_removed():
    forbidden = [
        ROOT / "cloud" / "vps" / "brain-termux-autodeploy.sh",
        ROOT / "android_executor" / "app" / "src" / "main" / "assets" / "brain-termux-autodeploy.sh",
    ]
    assert all(not p.exists() for p in forbidden)


def test_android_executor_has_no_termux_deploy_task():
    source = (ROOT / "android_executor" / "app" / "src" / "main" / "java" /
              "com" / "electronicbrain" / "androidexecutor" / "ExecutorService.kt").read_text(encoding="utf-8")
    assert "termux_vps_" not in source
    assert "runEmbeddedTerminal" not in source
