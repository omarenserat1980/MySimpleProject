import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"


class WindowsContractServiceApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(encoding="utf-8")
        start = cls.source.index('@app.post("/api/brain/windows/contract/issue")')
        end = cls.source.find("\n@app.", start + 1)
        cls.route = cls.source[start:] if end < 0 else cls.source[start:end]

    def test_contract_issue_route_is_explicit(self):
        self.assertIn('"/api/brain/windows/contract/issue"', self.route)
        self.assertIn("def brain_windows_contract_issue", self.route)

    def test_control_key_is_checked_before_contract_service(self):
        auth = self.route.index("require_control_key(request)")
        invoke = self.route.index("issue_windows_contract(body)")
        self.assertLess(auth, invoke)

    def test_route_uses_real_control_plane_issuer(self):
        self.assertIn("from .brain.windows_contract_service import issue as issue_windows_contract", self.route)
        self.assertNotIn("BRAIN_AUTHORITY_PRIVATE_KEY_B64", self.route)
        self.assertNotIn("BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64", self.route)

    def test_issuer_failures_do_not_return_success(self):
        self.assertIn("except (RuntimeError, PermissionError, ValueError)", self.route)
        self.assertIn('HTTPException(status_code=409, detail=str(exc))', self.route)
        self.assertIn('return {"ok": True, "contract": result}', self.route)


if __name__ == "__main__":
    unittest.main()
