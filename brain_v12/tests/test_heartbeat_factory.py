"""Contract tests for the zero-network Universal Heartbeat Factory core."""
from __future__ import annotations

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from brain_v12.brain.heartbeat_factory import (
    FunctionDefinition,
    HeartbeatConflict,
    HeartbeatFactory,
)


class HeartbeatFactoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "heartbeats.sqlite3"
        self.factory = HeartbeatFactory(self.path)
        self.addCleanup(self.factory.close)

    def register(self, *, function_id="brain.api", enabled=True, **kwargs):
        return self.factory.register_function(FunctionDefinition(
            function_id=function_id,
            name=kwargs.pop("name", function_id),
            category=kwargs.pop("category", "core"),
            enabled=enabled,
            source_of_truth=kwargs.pop("source_of_truth", "test_fixture"),
            **kwargs,
        ), now=100.0)

    def create(self, function_id="brain.api", **kwargs):
        return self.factory.create_heartbeat(
            function_id, worker_id="worker-test", node_id="node-test",
            mode="test", payload={"ok": True}, now=101.0, **kwargs
        )

    def test_register_is_idempotent_and_updates_existing_definition(self):
        first = self.register()
        second = self.register(name="renamed")
        self.assertEqual(first["function_id"], second["function_id"])
        self.assertEqual(len(self.factory.list_functions()), 1)
        self.assertEqual(second["name"], "renamed")

    def test_unknown_function_is_rejected(self):
        with self.assertRaisesRegex(KeyError, "FUNCTION_NOT_REGISTERED"):
            self.create("missing")

    def test_heartbeat_starts_created_and_sequence_is_monotonic(self):
        self.register()
        first = self.create()
        second = self.create()
        self.assertEqual(first["status"], "CREATED")
        self.assertEqual(first["sequence"], 1)
        self.assertEqual(second["sequence"], 2)
        self.assertNotEqual(first["heartbeat_id"], second["heartbeat_id"])

    def test_duplicate_sequence_with_changed_delivery_identity_conflicts(self):
        self.register()
        self.create(sequence=1)
        with self.assertRaises(HeartbeatConflict):
            self.factory.create_heartbeat(
                "brain.api", worker_id="worker-test", node_id="different-node",
                mode="test", sequence=1, payload={"ok": True}, now=101.0,
            )

    def test_explicit_duplicate_sequence_is_idempotent_for_same_payload(self):
        self.register()
        first = self.create(sequence=1)
        duplicate = self.create(sequence=1)
        self.assertEqual(first["heartbeat_id"], duplicate["heartbeat_id"])
        self.assertEqual(len(self.factory.db.execute("SELECT * FROM heartbeat_events").fetchall()), 1)

    def test_protected_function_requires_authorization_reference(self):
        self.register(function_id="remote.api", enabled=True, auth_required=True)
        with self.assertRaisesRegex(PermissionError, "AUTHORIZATION_REFERENCE_REQUIRED"):
            self.create("remote.api")
        accepted = self.factory.create_heartbeat(
            "remote.api", worker_id="worker-test", node_id="node-test", mode="test",
            authorization_ref="test-auth-fixture", now=101.0,
        )
        self.assertEqual(accepted["status"], "CREATED")

    def test_concurrent_emission_keeps_sequences_unique(self):
        self.register()
        def emit(_):
            return self.factory.create_heartbeat(
                "brain.api", worker_id="shared-worker", node_id="shared-node",
                mode="test", payload={"safe": True}, now=101.0,
            )
        with ThreadPoolExecutor(max_workers=8) as pool:
            rows = list(pool.map(emit, range(20)))
        self.assertEqual(sorted(row["sequence"] for row in rows), list(range(1, 21)))
        self.assertEqual(len({row["heartbeat_id"] for row in rows}), 20)

    def test_reused_sequence_with_different_payload_conflicts(self):
        self.register()
        self.create(sequence=1)
        with self.assertRaises(HeartbeatConflict):
            self.factory.create_heartbeat(
                "brain.api", worker_id="worker-test", node_id="node-test",
                mode="test", sequence=1, payload={"ok": False}, now=101.0,
            )

    def test_send_ack_and_verification_are_separate_transitions(self):
        self.register()
        heartbeat = self.create()
        heartbeat_id = heartbeat["heartbeat_id"]
        sent = self.factory.transition(heartbeat_id, "SENT", now=102.0)
        self.assertEqual(sent["status"], "SENT")
        self.assertIsNotNone(sent["sent_at"])
        ack = self.factory.transition(heartbeat_id, "ACKNOWLEDGED", now=103.0, latency_ms=4.5)
        self.assertEqual(ack["status"], "ACKNOWLEDGED")
        self.assertIsNotNone(ack["received_at"])
        with self.assertRaisesRegex(ValueError, "VERIFICATION_EVIDENCE_REQUIRED"):
            self.factory.transition(heartbeat_id, "VERIFIED", now=104.0)
        verified = self.factory.transition(
            heartbeat_id, "VERIFIED", now=104.0, evidence_ref="test-receiver:ack-1"
        )
        self.assertEqual(verified["status"], "VERIFIED")
        self.assertEqual(verified["evidence_ref"], "test-receiver:ack-1")

    def test_arbitrary_error_text_is_not_persisted(self):
        self.register()
        heartbeat = self.create()
        failed = self.factory.transition(
            heartbeat["heartbeat_id"], "FAILED", now=102.0,
            error_code="API_KEY=secret-value",
        )
        self.assertEqual(failed["error_code"], "UNCLASSIFIED_ERROR")
        raw = self.path.read_bytes()
        self.assertNotIn(b"secret-value", raw)

    def test_delayed_heartbeat_can_be_resent_without_duplicate_record(self):
        self.register()
        heartbeat = self.create()
        heartbeat_id = heartbeat["heartbeat_id"]
        self.factory.transition(heartbeat_id, "SENT", now=102.0)
        self.factory.transition(heartbeat_id, "DELAYED", now=110.0, error_code="ACK_TIMEOUT")
        resent = self.factory.transition(heartbeat_id, "SENT", now=111.0)
        self.assertEqual(resent["status"], "SENT")
        self.assertEqual(resent["sent_at"], 111.0)
        self.assertEqual(self.factory.summary()["heartbeats_total"], 1)

    def test_invalid_transition_cannot_skip_delivery_acknowledgement(self):
        self.register()
        heartbeat = self.create()
        with self.assertRaisesRegex(ValueError, "INVALID_HEARTBEAT_TRANSITION"):
            self.factory.transition(heartbeat["heartbeat_id"], "VERIFIED", evidence_ref="fake-proof")

    def test_secret_like_payload_keys_are_redacted_before_persistence(self):
        self.register()
        heartbeat = self.factory.create_heartbeat(
            "brain.api", worker_id="worker-test", node_id="node-test", mode="test",
            payload={"api_key": "never-store-me", "nested": {"password": "also-secret", "safe": 1}},
            now=101.0,
        )
        self.assertEqual(heartbeat["payload"]["api_key"], "[REDACTED]")
        self.assertEqual(heartbeat["payload"]["nested"]["password"], "[REDACTED]")
        stored = self.factory.db.execute("SELECT payload_json FROM heartbeat_events").fetchone()["payload_json"]
        self.assertNotIn("never-store-me", stored)
        self.assertNotIn("also-secret", stored)

    def test_registry_and_events_survive_restart(self):
        self.register()
        heartbeat = self.create()
        heartbeat_id = heartbeat["heartbeat_id"]
        self.factory.close()
        reopened = HeartbeatFactory(self.path)
        self.addCleanup(reopened.close)
        self.assertIsNotNone(reopened.get_function("brain.api"))
        self.assertEqual(reopened.get_heartbeat(heartbeat_id)["status"], "CREATED")

    def test_disabled_function_cannot_emit_heartbeat(self):
        self.register(function_id="disabled.probe", enabled=False)
        with self.assertRaisesRegex(RuntimeError, "FUNCTION_DISABLED"):
            self.create("disabled.probe")

    def test_simulated_functions_are_not_claimed_as_remote(self):
        self.register(function_id="asic.hashrate", enabled=True, category="simulation",
                      implementation="protocol_only", source_of_truth="simulated_fixture")
        self.factory.create_heartbeat(
            "asic.hashrate", worker_id="sim-worker", node_id="sim-node",
            mode="simulated", source="synthetic_fixture", payload={"hashrate": 0}, now=101.0,
        )
        summary = self.factory.summary()
        self.assertEqual(summary["mode"], "local_protocol_only")
        self.assertFalse(summary["remote_delivery_proven"])
        self.assertEqual(summary["functions_enabled"], 1)

    def test_execution_result_is_separate_from_delivery_verification(self):
        self.register(function_id="local.probe", enabled=True, implementation="local_read_only_probe")
        updated = self.factory.record_execution_result(
            "local.probe", "PASS", latency_ms=2.5, now=105.0
        )
        self.assertEqual(updated["last_execution_status"], "PASS")
        self.assertEqual(updated["last_execution_at"], 105.0)
        self.assertEqual(updated["last_execution_latency_ms"], 2.5)
        self.assertIsNone(updated["last_success_at"])
        self.assertEqual(updated["status"], "REGISTERED")

    def test_delayed_detection_only_reports_enabled_functions(self):
        self.register(function_id="enabled.one", enabled=True)
        self.register(function_id="disabled.one", enabled=False)
        delayed = self.factory.delayed_functions(now=200.0)
        self.assertEqual([x["function_id"] for x in delayed], ["enabled.one"])
        self.assertEqual(delayed[0]["status"], "DELAYED")

    def test_load_smoke_for_10_25_50_and_100_catalog_entries(self):
        # Synthetic local load only; no HTTP, cloud, worker, or paid service calls.
        for count in (10, 25, 50, 100):
            factory = HeartbeatFactory(":memory:")
            self.addCleanup(factory.close)
            for index in range(count):
                function_id = f"synthetic.{count}.{index}"
                factory.register_function(FunctionDefinition(
                    function_id=function_id, name=function_id, category="load-test",
                    interval_seconds=60, enabled=True, source_of_truth="synthetic_fixture",
                ), now=100.0)
                pulse = factory.create_heartbeat(
                    function_id, worker_id="load-worker", node_id="load-node",
                    mode="test", source="synthetic_fixture", now=101.0,
                )
                self.assertEqual(pulse["status"], "CREATED")
            self.assertEqual(factory.summary()["functions_registered"], count)
            self.assertEqual(factory.summary()["heartbeats_total"], count)


if __name__ == "__main__":
    unittest.main()
