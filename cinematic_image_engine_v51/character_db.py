from __future__ import annotations
import json
from pathlib import Path

class CharacterDB:
    def __init__(self, root):
        self.path=Path(root)/"characters"/"characters.json"
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if not self.path.exists(): self.path.write_text("{}",encoding="utf-8")

    def load(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def upsert(self, character_id, dna):
        data=self.load(); data[character_id]=dna
        self.path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        return data[character_id]

    def get(self, character_id):
        return self.load().get(character_id,{})
