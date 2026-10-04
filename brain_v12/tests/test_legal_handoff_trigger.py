import unittest

from brain_v12.brain.legal_handoff import LegalHandoff, HandoffState
from brain_v12.brain.legal_handoff_trigger import VerifiedFundsTrigger, prepare_lawyer_request


class LegalHandoffTriggerTests(unittest.TestCase):
    def _trigger(self, **kw):
        base = dict(
            available_funds_verified=True,
            available_amount=100.0,
            currency="JOD",
            evidence_refs=("fund-evidence-1",),
            contracting_authority_verified=True,
        )
        base.update(kw)
        return VerifiedFundsTrigger(**base)

    def test_verified_positive_funds_open_lawyer_request(self):
        handoff = LegalHandoff("FOUNDER_IDENTITY_REF")
        result = prepare_lawyer_request(
            handoff, self._trigger(), lawyer_contact_ref="LAWYER_CONTACT_REF"
        )
        self.assertEqual(result["status"], "LAWYER_REQUEST_READY")
        self.assertEqual(handoff.state, HandoffState.LEGAL_HANDOFF_PENDING)
        self.assertFalse(result["transfer_initiated"])

    def test_no_verified_funds_blocks(self):
        handoff = LegalHandoff("FOUNDER_IDENTITY_REF")
        result = prepare_lawyer_request(handoff, self._trigger(available_funds_verified=False))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(handoff.state, HandoffState.VERIFIED_FUNDS)

    def test_no_positive_amount_blocks(self):
        handoff = LegalHandoff("FOUNDER_IDENTITY_REF")
        result = prepare_lawyer_request(handoff, self._trigger(available_amount=0))
        self.assertEqual(result["status"], "BLOCKED")

    def test_authority_is_required(self):
        handoff = LegalHandoff("FOUNDER_IDENTITY_REF")
        result = prepare_lawyer_request(
            handoff, self._trigger(contracting_authority_verified=False)
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "LEGAL_AUTHORITY_REQUIRED")


if __name__ == "__main__":
    unittest.main()
