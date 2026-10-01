# BRAIN-0/1 Architecture

The machine executes encoded bytes. The visible 0/1 representation is a lossless representation of those bytes.

Migration:
1. deterministic VM
2. memory and persistent state
3. task engine and evidence chain
4. supervisor: plan -> execute -> verify -> repair -> retry
5. Termux Emulator adapter
6. media adapters
7. optional API/UI adapters

The low-level core has no FastAPI, Pydantic, Render, or network dependency.
