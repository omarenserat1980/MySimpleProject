from brain0.core import BrainVM,LOAD,ADD,VERIFY,HALT,encode
def test_binary_core():
    program=b"".join([encode(LOAD,1,7,0),encode(LOAD,2,5,0),encode(ADD,1,2,0),encode(VERIFY,1,12,0),encode(HALT)])
    vm=BrainVM()
    vm.load(program)
    result=vm.run()
    assert result["status"]=="VERIFIED_COMPLETED"
    assert result["registers"][1]==12
