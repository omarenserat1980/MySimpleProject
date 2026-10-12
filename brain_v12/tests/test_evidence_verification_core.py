from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.brain.verification_core import VerificationCore
from brain_v12.brain.brain_constitution import ConstitutionViolation

def test_ci_evidence_cannot_prove_runtime_success(tmp_path):
    store=EvidenceStore(tmp_path/"evidence.db")
    store.append("m1","ci",{"run":1},producer="github-actions")
    assert not VerificationCore(store).verify("m1").verified

def test_runtime_evidence_proves_success(tmp_path):
    store=EvidenceStore(tmp_path/"evidence.db")
    item=store.append("m1","settings_opened",{"ok":True},producer="android-executor")
    result=VerificationCore(store).assert_success("m1",required_kind="settings_opened")
    assert result.verified
    assert item["evidence_id"] in result.evidence_ids

def test_wrong_claim_is_rejected(tmp_path):
    store=EvidenceStore(tmp_path/"evidence.db")
    store.append("m1","other_claim",True,producer="executor")
    try: VerificationCore(store).assert_success("m1",required_kind="settings_opened")
    except ConstitutionViolation: pass
    else: raise AssertionError("success must require runtime evidence of the requested kind")
