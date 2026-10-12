"""Native media QC gate for BRAIN releases."""
from __future__ import annotations
import json,subprocess
from pathlib import Path
def probe(path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,size:stream=codec_type,codec_name,width,height,channels,sample_rate","-of","json",str(path)],capture_output=True,text=True)
    if p.returncode: return {"ok":False,"error":p.stderr[-1000:]}
    return {"ok":True,"data":json.loads(p.stdout)}
def validate(path,min_seconds=1):
    f=Path(path); errors=[]
    if not f.exists() or f.stat().st_size==0: errors.append("missing_master")
    else:
        q=probe(f)
        if not q["ok"]: errors.append("ffprobe_failed")
        else:
            streams=q["data"].get("streams",[]);fmt=q["data"].get("format",{})
            if not any(x.get("codec_type")=="video" for x in streams): errors.append("no_video")
            if not any(x.get("codec_type")=="audio" for x in streams): errors.append("no_audio")
            try:
                if float(fmt.get("duration",0))<min_seconds: errors.append("duration_too_short")
            except: errors.append("invalid_duration")
    return {"status":"PASS" if not errors else "FAIL","errors":errors}
if __name__=="__main__":
    import sys
    print(json.dumps(validate(sys.argv[1]),indent=2))
