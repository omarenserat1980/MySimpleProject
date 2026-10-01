from brain0.core import BrainVM,LOAD,ADD,VERIFY,TASK,HALT,encode
program=b"".join([
    encode(TASK,1,7,5),
    encode(LOAD,1,7,0),
    encode(LOAD,2,5,0),
    encode(ADD,1,2,0),
    encode(VERIFY,1,12,0),
    encode(HALT),
])
vm=BrainVM()
vm.load(program)
result=vm.run()
assert result["status"]=="VERIFIED_COMPLETED", result
assert result["registers"][1]==12, result
print("BRAIN-0/1 SELF TEST: VERIFIED")
print(result)
