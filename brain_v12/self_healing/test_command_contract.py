#!/usr/bin/env python3
"""Tests for the Brain command contract."""
from brain_v12.self_healing.command_contract import BRAIN_CONTINUE_AUTONOMOUSLY, command_name, is_continue, parse


def test_arabic_continue_command():
    command = parse("أكمل")
    assert command is not None
    assert command.name == BRAIN_CONTINUE_AUTONOMOUSLY
    assert command.autonomous is True


def test_continue_aliases():
    assert is_continue("تابع")
    assert is_continue("continue autonomously")
    assert is_continue("BRAIN_CONTINUE_AUTONOMOUSLY")


def test_unrelated_text_is_not_a_command():
    assert not is_continue("افحص فقط")


def test_whitespace_and_case_normalization():
    assert is_continue("  CONTINUE AUTONOMOUSLY  ")


def test_explicit_brain_command_alias():
    assert is_continue(BRAIN_CONTINUE_AUTONOMOUSLY)


def test_brain_owns_arabic_command_name():
    assert command_name("أكمل") == BRAIN_CONTINUE_AUTONOMOUSLY
