# BRAIN-0/1 implementation status

Implemented:
- deterministic bytecode VM
- instruction set
- kernel task state machine
- retrying supervisor
- memory layer
- tamper-evident SHA-256 evidence chain
- integrated runtime
- automated tests
- Termux adapter contract

Not yet migrated:
- existing FastAPI service
- existing cinematic factory
- real persistent database
- native ARM machine-code bootloader

Migration rule: never declare a layer migrated until an executable test proves it.
