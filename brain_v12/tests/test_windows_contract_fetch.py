"""Focused tests for the short-lived contract fetch client; no real secrets/network."""
from __future__ import annotations
import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from brain_v12.brain import fetch_windows_execution_contract as client

class FakeResponse:
    status = 200
    def __init__(self, payload): self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload

class ContractFetchTests(unittest.TestCase):
    def setUp(self):
        self.saved = {k: os.environ.get(k) for k in (
            "BRAIN_WINDOWS_CONTROL_PLANE_URL", "BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY",
            "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
            "BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE")}
        os.environ.update({
            "BRAIN_WINDOWS_CONTROL_PLANE_URL": "https://brain.example.invalid",
            "BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY": "test-only-placeholder",
            "GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "12345", "GITHUB_RUN_ATTEMPT": "2",
        })
        self.temp = tempfile.TemporaryDirectory()
        os.environ["BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE"] = str(Path(self.temp.name)/"contract.json")
        self.contract = {"schema":"brain.windows-execution-contract.v1",
            "source_commit":"a"*40,"task_id":"windows-server-2025-real-boot",
            "attempt_id":"github-12345-attempt-2","authority_signature":"test-signature",
            "expires_at":9999999999}
    def tearDown(self):
        self.temp.cleanup()
        for k,v in self.saved.items():
            if v is None: os.environ.pop(k,None)
            else: os.environ[k]=v
    def test_fetch_writes_bound_contract_with_restricted_permissions(self):
        with patch("brain_v12.brain.authority_signature.verify_contract_signature", return_value=True), \
             patch.object(client.urllib.request, "urlopen",
                          return_value=FakeResponse({"issued":True,"contract":self.contract})) as mocked:
            self.assertEqual(client.main(),0)
        req=mocked.call_args.args[0]
        self.assertEqual(req.full_url,"https://brain.example.invalid/api/brain/windows/contracts/issue")
        self.assertEqual(req.get_header("X-brain-contract-delivery-key"),"test-only-placeholder")
        path=Path(os.environ["BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE"])
        self.assertEqual(json.loads(path.read_text()),self.contract)
        self.assertEqual(path.stat().st_mode & 0o777,0o600)
    def test_rejects_contract_bound_to_different_attempt(self):
        bad=dict(self.contract,attempt_id="wrong-attempt")
        with patch.object(client.urllib.request,"urlopen",
                          return_value=FakeResponse({"issued":True,"contract":bad})):
            with self.assertRaisesRegex(RuntimeError,"BRAIN_CONTRACT_RESPONSE_BINDING_MISMATCH"):
                client.main()
    def test_rejects_invalid_authority_signature(self):
        with patch.object(client.urllib.request, "urlopen",
                          return_value=FakeResponse({"issued":True,"contract":self.contract})):
            with patch("brain_v12.brain.authority_signature.verify_contract_signature", return_value=False):
                with self.assertRaisesRegex(RuntimeError, "BRAIN_CONTRACT_AUTHORITY_SIGNATURE_INVALID"):
                    client.main()

    def test_rejects_expired_contract(self):
        expired = dict(self.contract, expires_at=1)
        with patch.object(client.urllib.request, "urlopen",
                          return_value=FakeResponse({"issued":True,"contract":expired})):
            with patch("brain_v12.brain.authority_signature.verify_contract_signature", return_value=True):
                with self.assertRaisesRegex(RuntimeError, "BRAIN_CONTRACT_EXPIRED"):
                    client.main()

    def test_rejects_plain_http_before_network(self):
        os.environ["BRAIN_WINDOWS_CONTROL_PLANE_URL"]="http://brain.example.invalid"
        with patch.object(client.urllib.request,"urlopen") as mocked:
            with self.assertRaisesRegex(RuntimeError,"BRAIN_WINDOWS_CONTROL_PLANE_HTTPS_REQUIRED"):
                client.main()
            mocked.assert_not_called()

if __name__=="__main__": unittest.main()
