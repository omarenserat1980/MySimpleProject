# BRAIN-0/1 Full Runtime

Executable verification core of Electronic Brain.

Layers:
1. Bytecode VM
2. Kernel task state machine
3. Supervisor with retry
4. Memory snapshot
5. Tamper-evident evidence chain
6. Integrated runtime
7. Termux task allowlist adapter

Verification commands:
`PYTHONPATH=. python brain0/programs/self_test.py`
`PYTHONPATH=. python brain0/programs/supervisor_test.py`
`PYTHONPATH=. python brain0/programs/runtime_test.py`
`python -m pytest -q brain0/tests`

A task is verified only when the VM produces VERIFIED_COMPLETED and the evidence chain validates.

The BRAIN-0/1 layer is a portable bytecode VM, not native ARM machine code.
