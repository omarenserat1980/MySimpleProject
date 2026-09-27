"""Persistent audio continuity state."""
from pathlib import Path
import json,time
class AudioContinuity:
 def __init__(self,path='audio_continuity.json'):
  self.path=Path(path); self.data=self._load()
 def _load(self):
  try:return json.loads(self.path.read_text('utf-8'))
  except Exception:return {'speakers':{},'spaces':{},'motifs':{},'shots':{}}
 def update(self,shot_id,evidence):
  self.data['shots'][shot_id]={**evidence,'updated_at':time.time()}; self.save()
 def context(self):return self.data
 def save(self):
  self.path.parent.mkdir(parents=True,exist_ok=True); t=self.path.with_suffix('.tmp'); t.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),'utf-8'); t.replace(self.path)
