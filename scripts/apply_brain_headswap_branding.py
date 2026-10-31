#!/usr/bin/env python3
"""Apply a minimal, reproducible Brain label and side-by-side debug package ID."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "third_party" / "headswap" / "android" / "app"
STRINGS = APP / "src/main/res/values/strings.xml"
GRADLE = APP / "build.gradle.kts"

text = STRINGS.read_text(encoding="utf-8")
old = '<string name="app_name" translatable="false">Headswap</string>'
new = '<string name="app_name" translatable="false">BRAIN CarLife Bridge</string>'
if new not in text:
    if old not in text:
        raise SystemExit("Expected upstream app_name string not found; refusing blind edit")
    STRINGS.write_text(text.replace(old, new, 1), encoding="utf-8")

gradle = GRADLE.read_text(encoding="utf-8")
needle = '        debug {\n            buildConfigField("boolean", "WIRELESS_BETA", "true")\n        }'
replacement = '        debug {\n            applicationIdSuffix = ".brain"\n            versionNameSuffix = "-brain"\n            buildConfigField("boolean", "WIRELESS_BETA", "true")\n        }'
if 'applicationIdSuffix = ".brain"' not in gradle:
    if needle not in gradle:
        raise SystemExit("Expected upstream debug buildType block not found; refusing blind edit")
    GRADLE.write_text(gradle.replace(needle, replacement, 1), encoding="utf-8")
print("Applied Brain debug overlay; upstream package remains separate and release config is untouched.")
