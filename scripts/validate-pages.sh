#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-brain_v12/web}"
SITE="${2:-_site}"

[[ -d "$ROOT" ]] || { echo "ERROR: missing web root: $ROOT"; exit 1; }
[[ -f "$ROOT/index.html" ]] || { echo "ERROR: missing index.html"; exit 1; }

rm -rf "$SITE"
mkdir -p "$SITE"
cp -R "$ROOT"/. "$SITE"/

required=(index.html code-tool.html)
for file in "${required[@]}"; do
  [[ -s "$SITE/$file" ]] || { echo "ERROR: missing required page: $file"; exit 1; }
done

grep -qi '<html' "$SITE/index.html" || { echo "ERROR: index.html is not HTML"; exit 1; }
grep -q 'العقل الإلكتروني' "$SITE/index.html" || { echo "ERROR: Brain V12 marker missing"; exit 1; }

# Validate local href/src targets that are explicitly referenced by HTML.
python3 - "$SITE" <<'PY'
from pathlib import Path
import re, sys
from urllib.parse import urlparse

site = Path(sys.argv[1]).resolve()
errors = []

for page in site.rglob("*.html"):
    text = page.read_text(encoding="utf-8", errors="replace")
    for attr, raw in re.findall(r'\b(href|src)\s*=\s*["\']([^"\']+)["\']', text, re.I):
        value = raw.strip()
        if not value or value.startswith(("#", "data:", "mailto:", "tel:", "javascript:")):
            continue
        parsed = urlparse(value)
        if parsed.scheme or parsed.netloc:
            continue
        target = (page.parent / parsed.path.lstrip("/")).resolve() if parsed.path.startswith("/") else (page.parent / parsed.path).resolve()
        try:
            target.relative_to(site)
        except ValueError:
            errors.append(f"{page.relative_to(site)} -> escapes site: {value}")
            continue
        if not target.exists():
            errors.append(f"{page.relative_to(site)} -> missing: {value}")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"Pages validation OK: {len(list(site.rglob('*.html')))} HTML files")
PY
