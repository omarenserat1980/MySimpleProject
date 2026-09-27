"""Bounded self-improvement from production failures; policy only."""
from pathlib import Path
import json,time
class SelfImprovement:
 def __init__(self,path='production_policy.json'):
  self.path=Path(path); self.data=self._load()
 def _load(self):
  try:return json.loads(self.path.read_text('utf-8'))
  except Exception:return {'version':1,'rules':[],'patterns':{},'history':[]}
 def observe(self,shot_id,result):
  qc=result.get('film_qc') or result.get('visual_qc') or {}; failures=[k for k,v in qc.get('checks',{}).items() if v is False]
  for f in failures:self.data['patterns'][f]=self.data['patterns'].get(f,0)+1
  self.data['history'].append({'shot_id':shot_id,'failures':failures,'ts':time.time()}); self._derive(); self.save()
 def _derive(self):
  actions={'identity':'increase_reference_anchor_strength','world':'increase_world_state_context','temporal':'reduce_motion_complexity','audio':'lock_acoustic_and_speaker_state','visual':'tighten_lighting_and_composition_constraints','story':'increase_beat_traceability','factuality':'block_unverified_claims'}
  self.data['rules']=[{'dimension':k,'action':actions.get(k,'tighten_qc'),'confidence':min(.95,.5+.1*v)} for k,v in self.data['patterns'].items() if v>=2]
 def context(self):return {'rules':self.data['rules'],'patterns':self.data['patterns']}
 def save(self):
  self.path.parent.mkdir(parents=True,exist_ok=True); t=self.path.with_suffix('.tmp'); t.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),'utf-8'); t.replace(self.path)
