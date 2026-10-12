"""Compatibility import for the canonical V12 Brain Supervisor.

The system-level Supervisor implementation lives only in
:mod:`brain_v12.brain.brain_supervisor`.  This module intentionally contains
no second policy implementation.
"""
from .brain_supervisor import BrainSupervisor

__all__ = ["BrainSupervisor"]
