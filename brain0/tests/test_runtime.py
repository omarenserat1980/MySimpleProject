from brain0.core import LOAD,ADD,VERIFY,HALT,encode
from brain0.runtime import BrainRuntime
def test_full_runtime():
    program=b"".join([encode(LOAD,1,7,0),encode(LOAD,2,5,0),encode(ADD,1,2,0),encode(VERIFY,1,12,0),encode(HALT)])
    r=BrainRuntime().run("runtime-001",program)
    assert r["status"]=="VERIFIED_COMPLETED"
    assert r["evidence_chain_valid"]
