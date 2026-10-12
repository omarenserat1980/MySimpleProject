from brain_v12.brain.cloud_hardware import CPU,Memory,GPU,Storage,Network,Firmware,Management,Availability,HardwareManifest,WorkloadRequirement
from brain_v12.brain.cloud_resource_fabric import CloudResourceFabric

def node(name,state="online"):
    return HardwareManifest(name,"cpu",state,"observed",CPU("x86_64",1,32,64),Memory(256*1024**3),GPU("none",0,0),Storage(2*1024**4),Network(10_000_000_000),Firmware(True,True),Management(),Availability(),{"kvm":True})

def test_single_flight():
    f=CloudResourceFabric(); f.register(node("cpu-01")); r=WorkloadRequirement(cpu_threads=4)
    assert f.acquire("a",r,now=100)["status"]=="LEASE_ACQUIRED"
    assert f.acquire("b",r,now=100)["status"]=="NO_CAPABLE_EXECUTOR"

def test_idempotent():
    f=CloudResourceFabric(); f.register(node("cpu-01")); r=WorkloadRequirement(cpu_threads=4)
    a=f.acquire("a",r,now=100); b=f.acquire("a",r,now=101)
    assert a["executor_id"]==b["executor_id"] and b["status"]=="ALREADY_LEASED"

def test_expiry():
    f=CloudResourceFabric(); f.register(node("cpu-01")); r=WorkloadRequirement(cpu_threads=4)
    f.acquire("a",r,lease_seconds=10,now=100)
    assert f.reap_expired(now=111)==["a"]
    assert f.acquire("b",r,now=112)["status"]=="LEASE_ACQUIRED"

def test_quarantine():
    f=CloudResourceFabric(); f.register(node("cpu-01")); r=WorkloadRequirement(cpu_threads=4)
    f.acquire("a",r,now=100); assert f.quarantine("cpu-01","heartbeat_timeout")["status"]=="QUARANTINED"
    assert f.leases["a"].state=="REVOKED"
    assert f.acquire("b",r,now=101)["status"]=="NO_CAPABLE_EXECUTOR"
