"""Tests for the explicitly gated one-share TLS transport adapter."""
import json
import os
import socket
import ssl
import unittest
from unittest.mock import MagicMock, patch

from brain_v12.brain.stratum_tls_one_share_transport import (
    StratumTLSTransportError,
    send_one_share,
)
from brain_v12.brain.stratum_v1_protocol import StratumV1Session


def _authorized_session():
    session = StratumV1Session(username="worker.01", password="not-a-real-secret")
    session.subscribed = True
    session.authorized = True
    session.current_job_id = "job-1"
    session.active_job_ids.add("job-1")
    session.extranonce2_size = 2
    request = json.loads(session.request_submit(
        "job-1", "aabb", "00000001", "00000002"
    ).decode("utf-8"))
    return session, request


def _tls_socket(response):
    sock = MagicMock(spec=ssl.SSLSocket)
    context = MagicMock(spec=ssl.SSLContext)
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    sock.context = context
    sock.getpeercert.return_value = b"test-certificate"
    sock.cipher.return_value = ("TLS_AES_128_GCM_SHA256", "TLSv1.3", 128)
    reader = MagicMock()
    reader.readline.return_value = response
    sock.makefile.return_value = reader
    return sock, reader


class StratumTLSOneShareTransportTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "BRAIN_ENABLE_LIVE_STRATUM_SUBMIT": "1",
            "BRAIN_MINING_WORKER_OWNED": "1",
            "BRAIN_MINING_AUTHORIZED": "1",
            "BRAIN_LIVE_SUBMISSION_CONFIRM": "SUBMIT_ONE_SHARE",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_live_submit_is_forbidden_in_ci_before_socket_io(self):
        session, request = _authorized_session()
        sock, _ = _tls_socket(b'{"id":1,"result":true,"error":null}\n')
        with patch.dict(os.environ, {"CI": "true"}):
            with self.assertRaisesRegex(StratumTLSTransportError, "FORBIDDEN_IN_CI"):
                send_one_share(session, sock, request)
        sock.sendall.assert_not_called()

    def test_disabled_or_missing_explicit_confirmation_fails_closed(self):
        session, request = _authorized_session()
        sock, _ = _tls_socket(b'{"id":1,"result":true,"error":null}\n')
        with patch.dict(os.environ, {"BRAIN_LIVE_SUBMISSION_CONFIRM": "YES"}):
            with self.assertRaisesRegex(StratumTLSTransportError, "CONFIRMATION_REQUIRED"):
                send_one_share(session, sock, request)
        sock.sendall.assert_not_called()

    def test_plain_socket_is_rejected(self):
        session, request = _authorized_session()
        with self.assertRaisesRegex(StratumTLSTransportError, "VERIFIED_TLS_SOCKET_REQUIRED"):
            send_one_share(session, socket.socket(), request)

    def test_request_must_match_pending_share_and_current_job(self):
        session, request = _authorized_session()
        sock, _ = _tls_socket(b'{"id":1,"result":true,"error":null}\n')
        request["id"] = 99
        with self.assertRaisesRegex(StratumTLSTransportError, "PENDING_SHARE_REQUIRED"):
            send_one_share(session, sock, request)
        sock.sendall.assert_not_called()

    def test_one_share_reply_is_correlated_but_not_payout_proof(self):
        session, request = _authorized_session()
        sock, reader = _tls_socket(b'{"id":1,"result":true,"error":null}\n')
        result = send_one_share(session, sock, request)
        self.assertEqual(result["status"], "POOL_REPORTED_SHARE_ACCEPTED")
        self.assertTrue(result["pool_acceptance_response_observed"])
        self.assertFalse(result["independent_share_validation_verified"])
        self.assertFalse(result["payout_verified"])
        self.assertFalse(result["revenue_verified"])
        self.assertEqual(session.accepted_shares, 1)
        sock.sendall.assert_called_once()
        sent = json.loads(sock.sendall.call_args.args[0].decode("utf-8"))
        self.assertEqual(sent["method"], "mining.submit")
        self.assertEqual(sent["id"], request["id"])
        reader.close.assert_called_once()

    def test_pool_rejection_is_reported_without_claiming_success(self):
        session, request = _authorized_session()
        sock, _ = _tls_socket(b'{"id":1,"result":false,"error":[20,"details",null]}\n')
        result = send_one_share(session, sock, request)
        self.assertEqual(result["status"], "POOL_REPORTED_SHARE_REJECTED")
        self.assertFalse(result["pool_acceptance_response_observed"])
        self.assertFalse(result["revenue_verified"])

    def test_unverified_tls_context_fails_before_send(self):
        session, request = _authorized_session()
        sock, _ = _tls_socket(b'{"id":1,"result":true,"error":null}\\n')
        sock.context.verify_mode = ssl.CERT_NONE
        with self.assertRaisesRegex(StratumTLSTransportError, "CERTIFICATE_AND_HOSTNAME_VERIFICATION_REQUIRED"):
            send_one_share(session, sock, request)
        sock.sendall.assert_not_called()

    def test_unverified_peer_certificate_fails_before_send(self):
        session, request = _authorized_session()
        sock, _ = _tls_socket(b'{"id":1,"result":true,"error":null}\n')
        sock.getpeercert.return_value = b""
        with self.assertRaisesRegex(StratumTLSTransportError, "CERTIFICATE_REQUIRED"):
            send_one_share(session, sock, request)
        sock.sendall.assert_not_called()


if __name__ == "__main__":
    unittest.main()
