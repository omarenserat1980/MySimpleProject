from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "brain-chat.html"

def test_brain_chat_contract():
    html = PAGE.read_text(encoding="utf-8")
    for marker in (
        'fetch("/api/chat"',
        '/api/ai/status',
        '/api/image-factory/generate',
        'localStorage',
        'Brain Chat',
    ):
        assert marker in html, marker
