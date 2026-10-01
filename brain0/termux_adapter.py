"""Safe adapter contract for the BRAIN Termux Emulator.

This module does not execute arbitrary shell commands. It only describes
allowlisted Brain tasks for the existing emulator bridge.
"""
ALLOWED_TASKS={"status","python_version","brain_home","platform","brain0_self_test"}

def accept_task(task_type):
    if task_type not in ALLOWED_TASKS:
        raise ValueError("TASK_NOT_ALLOWED")
    return {"accepted":True,"task_type":task_type}
