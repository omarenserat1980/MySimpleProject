"""Cryptographic enrollment and attestation contract for native Windows nodes.

The server receives no execution authority merely by presenting an agent key.
Enrollment binds the node identity to Brain generation, network generation and
an explicit challenge. Attestation is a signed statement over those exact
values plus the executor identity. This module verifies the statement but
never stores the secret used to produce it.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any


WINDOWS_NATIVE_ATTESTATION_V1 = "windows-native-attestation-v1"


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def attestation_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def verify_attestation(
    *,
    payload: dict[str, Any],
    signature: str,
    signing_token: str,
) -> bool:
    if not signing_token or not signature:
        return False
    expected = hmac.new(
        signing_token.encode(),
        _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@dataclass(frozen=True)
class WindowsNativeEnrollment:
    enrollment_id: str
    executor_id: str
    server_id: str
    brain_id: str
    brain_generation: int
    network_generation: int
    challenge: str
    platform: str
    architecture: str
    attestation_version: str = WINDOWS_NATIVE_ATTESTATION_V1

    def validate(self) -> None:
        for name, value in (
            ("enrollment_id", self.enrollment_id),
            ("executor_id", self.executor_id),
            ("server_id", self.server_id),
            ("brain_id", self.brain_id),
            ("challenge", self.challenge),
            ("platform", self.platform),
            ("architecture", self.architecture),
        ):
            if not str(value).strip():
                raise ValueError(f"windows_native_{name}_required")
        if self.brain_generation < 1:
            raise ValueError("windows_native_brain_generation_invalid")
        if self.network_generation < 1:
            raise ValueError("windows_native_network_generation_invalid")
        if self.attestation_version != WINDOWS_NATIVE_ATTESTATION_V1:
            raise ValueError("windows_native_attestation_version_invalid")

    def attestation_payload(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema": self.attestation_version,
            "enrollment_id": self.enrollment_id,
            "executor_id": self.executor_id,
            "server_id": self.server_id,
            "brain_id": self.brain_id,
            "brain_generation": self.brain_generation,
            "network_generation": self.network_generation,
            "challenge": self.challenge,
            "platform": self.platform,
            "architecture": self.architecture,
        }

    def verify(self, signature: str, signing_token: str) -> dict[str, Any]:
        payload = self.attestation_payload()
        verified = verify_attestation(
            payload=payload,
            signature=signature,
            signing_token=signing_token,
        )
        return {
            "verified": verified,
            "schema": self.attestation_version,
            "enrollment_id": self.enrollment_id,
            "executor_id": self.executor_id,
            "server_id": self.server_id,
            "brain_generation": self.brain_generation,
            "network_generation": self.network_generation,
            "attestation_digest": attestation_digest(payload),
        }
