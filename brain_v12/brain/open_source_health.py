"""Probe optional open-source services without making them mandatory."""
from __future__ import annotations
import json, os, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from brain_v12.brain.open_source_stack import capabilities

OUT=Path("brain6_artifacts"); OUT.mkdir(exist_ok=True)

def probe(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Brain-OSS-Health/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=3) as r:
            return {"available":True,"status":int(getattr(r,"status",200))}
    except Exception as e:
        return {"available":False,"error":str(e)[:180]}

def main():
    rows=[]
    for t in capabilities():
        endpoint=t.get("endpoint")
        rows.append({
            "id":t["id"],"name":t["name"],"role":t["role"],
            "license":t["license"],"mode":t["mode"],
            "capabilities":t["capabilities"],
            "endpoint":endpoint,
            "health":probe(endpoint) if endpoint else {"available":False,"status":"model_or_external_setup_required"},
        })
    report={
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "policy":{"optional":True,"no_download_of_large_models":True,
                "no_service_required_for_core_brain":True},
      "components":rows,
    }
    (OUT/"open_source_stack_status.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    available=sum(x["health"].get("available",False) for x in rows)
    print(json.dumps({"ok":True,"components":len(rows),"services_available":available}))
if __name__=="__main__": main()
