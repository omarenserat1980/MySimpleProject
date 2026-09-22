"""Media metadata and routing layer; actual AI inference is provider-backed."""
import mimetypes, os

class MediaEngine:
    def inspect(self, path: str, content_type: str | None = None):
        size = os.path.getsize(path) if os.path.exists(path) else 0
        kind = (content_type or mimetypes.guess_type(path)[0] or "application/octet-stream").split("/")[0]
        return {"path":path,"kind":kind,"content_type":content_type,"size":size,
                "ai_analysis":"provider_required","status":"READY"}
