from brain0.core import LOAD,ADD,VERIFY,HALT,encode
from brain0.runtime import BrainRuntime
program=b"".join([encode(LOAD,1,7,0),encode(LOAD,2,5,0),encode(ADD,1,2,0),encode(VERIFY,1,12,0),encode(HALT)])
r=BrainRuntime().run("runtime-proof-001",program)
assert r["status"]=="VERIFIED_COMPLETED",r
assert r["evidence_chain_valid"] is True
assert r["memory"]["values"]["last_status"]=="VERIFIED_COMPLETED"
print("BRAIN-0/1 FULL RUNTIME: VERIFIED")
print(r)
