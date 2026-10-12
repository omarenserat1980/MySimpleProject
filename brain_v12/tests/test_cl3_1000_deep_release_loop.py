import hashlib
import unittest
from brain_v12.business.cl_000003_master_release_gate import REQUIRED,decide
from brain_v12.business.cl_000003_publication_guard import require_master_release
class ThousandDeepReleaseLoopTests(unittest.TestCase):
    def valid(self,i):
        artifact=hashlib.sha256(f"artifact-{i}".encode()).hexdigest()
        return {"film_id":f"CL3-FILM-{i:04d}","film_version":f"v{i%17+1}","production_run":f"RUN-{i:04d}","artifact_sha256":artifact,
                **{k:{"passed":True,"evidence_ref":f"CL3-FILM-{i:04d}/v{i%17+1}/RUN-{i:04d}/{k}/qc.json","evidence_sha256":hashlib.sha256(f"{i}:{k}".encode()).hexdigest(),"reviewed_artifact_sha256":artifact} for k in REQUIRED}}
    def mutate(self,e,i):
        a=i%10
        if a==0:e.pop("film_id",None)
        elif a==1:e.pop("film_version",None)
        elif a==2:e.pop("production_run",None)
        elif a==3:e["cinematic"]["passed"]=False
        elif a==4:e["rights"].pop("evidence_ref",None)
        elif a==5:e["legal_policy"].pop("evidence_sha256",None)
        elif a==6:e["technical"]["evidence_sha256"]="x"
        elif a==7:e["status"]="MASTER_RELEASE_PASS";e["publish_authorized"]=True;e["cinematic"]["passed"]=False
        elif a==8:e["film_id"]=" "
        elif a==9:e["legal_policy"]["passed"]=False
        return e
    def test_1000_real_adversarial_iterations(self):
        blocked=0; unexpected=[]
        for i in range(1000):
            e=self.mutate(self.valid(i),i); d=decide(e); p=require_master_release(e)
            if d["publish_authorized"] or p["authorized"]:unexpected.append(i)
            else:blocked+=1
        self.assertEqual(blocked,1000);self.assertEqual(unexpected,[])
if __name__=="__main__":unittest.main()
