from brain0.core import LOAD,ADD,VERIFY,HALT,encode
from brain0.supervisor import BrainSupervisor
def test_kernel_and_supervisor():
    program=b"".join([encode(LOAD,1,7,0),encode(LOAD,2,5,0),encode(ADD,1,2,0),encode(VERIFY,1,12,0),encode(HALT)])
    s=BrainSupervisor(max_retries=2)
    out=s.run("test-001",program)
    assert out["status"]=="VERIFIED_COMPLETED"
    assert s.kernel.tasks["test-001"].state=="SUCCESS"
    assert any(e["event"]=="TASK_VERIFIED" for e in s.kernel.audit)
