"""Payment verification and payout adapters.

Default mode is VERIFY_ONLY. Payout requires an explicit authorization token
and credentials supplied outside the repository. Brain never receives private keys.
"""
from __future__ import annotations
import hashlib,hmac,json,os,time,urllib.request

class PaymentAdapter:
    name="base"
    def verify_receipt(self, receipt): raise NotImplementedError
    def payout(self, request, authorization): raise NotImplementedError

class BaseUSDCAdapter(PaymentAdapter):
    name="base_usdc"
    def verify_receipt(self, receipt):
        tx=receipt.get("tx_hash")
        return {"verified":bool(tx and receipt.get("network") in {"base","base-mainnet"}),
                "evidence":{"tx_hash":tx,"network":receipt.get("network"),"source":receipt.get("source")}}
    def payout(self, request, authorization):
        if os.getenv("BRAIN_PAYOUT_ENABLED")!="1": return {"status":"DISABLED","reason":"payout_adapter_disabled"}
        if not authorization or authorization.get("approved") is not True: return {"status":"HUMAN_REVIEW"}
        # Deliberately no private key/signing implementation.
        return {"status":"READY_FOR_EXTERNAL_SIGNER","destination":request.get("destination"),
                "amount":request.get("amount"),"currency":request.get("currency")}

class BinanceAdapter(PaymentAdapter):
    """Optional outbound adapter. Credentials remain in a secret manager/env."""
    name="binance"
    def verify_receipt(self, receipt):
        return {"verified":bool(receipt.get("transaction_id") or receipt.get("tx_id")),
                "evidence":{"transaction_id":receipt.get("transaction_id") or receipt.get("tx_id"),
                            "source":receipt.get("source","binance")}}
    def payout(self, request, authorization):
        if os.getenv("BRAIN_BINANCE_PAYOUT_ENABLED")!="1": return {"status":"DISABLED","reason":"binance_payout_disabled"}
        if not authorization or authorization.get("approved") is not True: return {"status":"HUMAN_REVIEW"}
        required={"destination","amount","currency"}
        if not required.issubset(request): return {"status":"DENIED","reason":"incomplete_request"}
        return {"status":"READY_FOR_BINANCE_SIGNED_CALL","request":request}

def receipt_hash(receipt):
    return hashlib.sha256(json.dumps(receipt,sort_keys=True).encode()).hexdigest()
