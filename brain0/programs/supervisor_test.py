from brain0.core import LOAD,ADD,VERIFY,HALT,encode
from brain0.supervisor import BrainSupervisor
program=b"".join([encode(LOAD,1,7,0),encode(LOAD,2,5,0),encode(ADD,1,2,0),encode(VERIFY,1,12,0),encode(HALT)])
s=BrainSupervisor(max_retries=2)
out=s.run("brain0-proof-001",program)
assert out["status"]=="VERIFIED_COMPLETED",out
assert s.kernel.tasks["brain0-proof-001"].state=="SUCCESS"
print("BRAIN SUPERVISOR: VERIFIED")
print(out)
