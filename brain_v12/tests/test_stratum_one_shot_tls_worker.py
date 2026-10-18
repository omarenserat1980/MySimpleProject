"""Safety and bounded-input tests for the one-shot live worker; no network is used."""
import os
import unittest
from unittest.mock import patch

from brain_v12.brain.stratum_one_shot_tls_worker import (
    OneShotWorkerError,
    run_one_bounded_attempt,
)


AUTH = {
    "BRAIN_ENABLE_LIVE_STRATUM_WORKER": "1",
    "BRAIN_MINING_WORKER_OWNED": "1",
    "BRAIN_MINING_AUTHORIZED": "1",
    "BRAIN_LIVE_WORKER_CONFIRM": "RUN_ONE_BOUNDED_ATTEMPT",
    "BRAIN_LIVE_SUBMISSION_CONFIRM": "SUBMIT_ONE_SHARE",
    "BRAIN_STRATUM_PREVHASH_DIALECT_CONFIRMED": "1",
}


class OneShotTLSWorkerTests(unittest.TestCase):
    def test_disabled_by_default_and_never_opens_socket(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "brain_v12.brain.stratum_one_shot_tls_worker.socket.create_connection"
        ) as connect:
            with self.assertRaisesRegex(OneShotWorkerError, "LIVE_WORKER_DISABLED"):
                run_one_bounded_attempt(
                    host="pool.example", port=443, worker_name="worker.1",
                    worker_password="fixture-password",
                )
        connect.assert_not_called()

    def test_ci_forbids_live_worker_before_socket_io(self):
        with patch.dict(os.environ, {**AUTH, "CI": "true"}, clear=True), patch(
            "brain_v12.brain.stratum_one_shot_tls_worker.socket.create_connection"
        ) as connect:
            with self.assertRaisesRegex(OneShotWorkerError, "FORBIDDEN_IN_CI"):
                run_one_bounded_attempt(
                    host="pool.example", port=443, worker_name="worker.1",
                    worker_password="fixture-password",
                )
        connect.assert_not_called()

    def test_missing_explicit_one_share_confirmation_fails_closed(self):
        env = {key: value for key, value in AUTH.items()
               if key != "BRAIN_LIVE_SUBMISSION_CONFIRM"}
        with patch.dict(os.environ, env, clear=True), patch(
            "brain_v12.brain.stratum_one_shot_tls_worker.socket.create_connection"
        ) as connect:
            with self.assertRaisesRegex(
                OneShotWorkerError, "ONE_SHARE_SUBMISSION_CONFIRMATION_REQUIRED"
            ):
                run_one_bounded_attempt(
                    host="pool.example", port=443, worker_name="worker.1",
                    worker_password="fixture-password",
                )
        connect.assert_not_called()

    def test_unconfirmed_prevhash_dialect_fails_closed(self):
        env = {key: value for key, value in AUTH.items()
               if key != "BRAIN_STRATUM_PREVHASH_DIALECT_CONFIRMED"}
        with patch.dict(os.environ, env, clear=True), patch(
            "brain_v12.brain.stratum_one_shot_tls_worker.socket.create_connection"
        ) as connect:
            with self.assertRaisesRegex(
                OneShotWorkerError, "POOL_PREVHASH_DIALECT_CONFIRMATION_REQUIRED"
            ):
                run_one_bounded_attempt(
                    host="pool.example", port=443, worker_name="worker.1",
                    worker_password="fixture-password",
                )
        connect.assert_not_called()

    def test_attempt_count_is_bounded_before_connect(self):
        with patch.dict(os.environ, AUTH, clear=True), patch(
            "brain_v12.brain.stratum_one_shot_tls_worker.socket.create_connection"
        ) as connect:
            with self.assertRaisesRegex(OneShotWorkerError, "MAX_ATTEMPTS_OUT_OF_RANGE"):
                run_one_bounded_attempt(
                    host="pool.example", port=443, worker_name="worker.1",
                    worker_password="fixture-password", max_attempts=4097,
                )
        connect.assert_not_called()

    def test_credentials_and_host_are_validated_before_connect(self):
        with patch.dict(os.environ, AUTH, clear=True), patch(
            "brain_v12.brain.stratum_one_shot_tls_worker.socket.create_connection"
        ) as connect:
            with self.assertRaisesRegex(OneShotWorkerError, "INVALID_WORKER_PASSWORD"):
                run_one_bounded_attempt(
                    host="pool.example", port=443, worker_name="worker.1",
                    worker_password="bad\npassword",
                )
        connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
