#!/usr/bin/env python3
"""Tests for the Brain command contract."""
from brain_v12.self_healing.command_contract import is_continue, parse


def test_arabic_continue_command():
    command = parse("أكمل")
    assert command is not None
    assert command.name == "BRAIN_CONTINUE_AUTONOMOUSLY"
    assert command.autonomous is True


def test_continue_aliases():
    assert is_continue("تابع")
    assert is_continue("continue autonomously")
    assert is_continue("BRAIN_CONTINUE_AUTONOMOUSLY")


def test_unrelated_text_is_not_a_command():
    assert not is_continue("افحص فقط")
