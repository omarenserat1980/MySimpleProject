from brain_v7.braincore_v2.payout_policy import PayoutPolicy,authorize
from brain_v7.braincore_v2.payout_ledger import LedgerEntry,append,request_id,reconcile
from brain_v7.braincore_v2.payout_router import PayoutRouter
from brain_v7.braincore_v2.payout_reconciliation import check

def test_limits_and_allowlist_block():
    p=PayoutPolicy(100,100,0,("wallet-1",))
    assert authorize(101,"wallet-1",0,p)["allowed"] is False
    assert authorize(50,"wallet-2",0,p)["allowed"] is False

def test_idempotency():
    rid=request_id(10,"wallet-1","x")
    e=LedgerEntry(rid,10,"wallet-1","APPROVAL_REQUIRED")
    assert len(append(append([],e),e))==1

def test_confirm_requires_provider_reference():
    e=LedgerEntry("r",10,"w","SUBMITTED")
    try: reconcile(e,"CONFIRMED",None); assert False
    except ValueError: pass

def test_router_blocks_daily_limit():
    r=PayoutRouter(PayoutPolicy(100,100,0,("w",)),[])
    out=r.prepare(60,"w","n",50,"test")
    assert out["status"]=="BLOCKED"

def test_reconciliation_detects_mismatch():
    assert check(100,"CONFIRMED",90,"tx")["reconciled"] is False
