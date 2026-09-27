from pathlib import Path
import argparse
from .orchestrator import ImageFactory

def main():
    p=argparse.ArgumentParser(description="Electronic Brain Cinematic Image Engine V5.1")
    p.add_argument("script"); p.add_argument("--project",default="./projects/default")
    p.add_argument("--project-id"); p.add_argument("--retries",type=int,default=5)
    a=p.parse_args()
    script=Path(a.script).read_text(encoding="utf-8")
    f=ImageFactory(a.project,max_retries=a.retries); s=f.initialize(a.project_id)
    f.prepare(s,script); s=f.run(s); print(f"STATUS={s.status}"); print(f"PROJECT={a.project}")
if __name__=="__main__": main()
