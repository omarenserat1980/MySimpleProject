from __future__ import annotations
from .canonical import CanonicalQuranAdapter

class TafsirAdapter:
    """Read-only tafsir/resource adapter; returned material remains tagged as tafsir."""
    def __init__(self, canonical: CanonicalQuranAdapter | None = None):
        self.quran = canonical or CanonicalQuranAdapter()

    def resources(self, language: str = "ar") -> dict:
        return self.quran._get("/content/api/v4/resources/tafsirs", {"language": language})

    def ayah(self, resource_id: int, ayah_key: str) -> dict:
        return self.quran._get(f"/content/api/v4/tafsirs/{resource_id}/by_ayah/{ayah_key}")
