#!/usr/bin/env python3
"""One safe entry point for the never-ending Brain improvement loop."""
from __future__ import annotations
import os
from brain_v12.tools.brain_runtime_supervisor import main

if __name__ == "__main__":
    # The supervisor itself owns the endless loop; this file is the single command.
    os.environ.setdefault("BRAIN_SUPERVISOR_INTERVAL", "60")
    main()
