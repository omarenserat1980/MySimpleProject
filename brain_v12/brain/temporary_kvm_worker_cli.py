#!/usr/bin/env python3
"""Brain CLI for discovering and requesting a temporary real-KVM worker.

Discovery is side-effect free. Provisioning delegates to the configured
TemporaryKVMWorkerProvisioner backend and therefore cannot fabricate KVM.
"""
from __future__ import annotations
import argparse,json
from .temporary_kvm_options import default_options,rank_options
from .temporary_kvm_worker_provisioner import TemporaryKVMWorkerProvisioner

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("options")
    a=sub.add_parser("provision")
    a.add_argument("--timeout",type=int,default=120)
    args=p.parse_args()
    if args.cmd=="options":
        accepted,rejected=rank_options(default_options())
        print(json.dumps({"accepted":[x.__dict__ for x in accepted],
                          "rejected":[{"provider":p,"reason":r} for p,r in rejected]},indent=2))
        return 0
    lease=TemporaryKVMWorkerProvisioner().provision_once(args.timeout)
    print(json.dumps(lease.to_dict(),indent=2,sort_keys=True))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
