"""Free/open-source Web game generator with deterministic release manifest."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import html

@dataclass(frozen=True)
class WebGameRelease:
    game_id: str
    title: str
    version: str
    entrypoint: str
    status: str
    sha256: str

class WebGameFactory:
    def build(self, game_id: str, title: str, version: str = "1.0.0") -> tuple[str, WebGameRelease]:
        safe=html.escape(title)
        doc=f"""<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{safe}</title><style>body{{margin:0;background:#08101d;color:#fff;font-family:system-ui;text-align:center}}main{{max-width:620px;margin:8vh auto;padding:24px}}button{{font:inherit;padding:14px 22px;border:0;border-radius:14px;cursor:pointer}}#score{{font-size:48px;margin:30px}}</style><main><h1>🎮 {safe}</h1><p>اضغط بسرعة واجمع النقاط.</p><div id="score">0</div><button id="play">ابدأ</button><script>let s=0;play.onclick=()=>{{s++;score.textContent=s}}</script></main>"""
        digest=sha256(doc.encode()).hexdigest()
        release=WebGameRelease(game_id,title,version,"index.html","BUILT",digest)
        return doc,release

    def manifest(self, release: WebGameRelease) -> dict:
        return asdict(release)
