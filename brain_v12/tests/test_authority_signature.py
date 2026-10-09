import base64, unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from brain_v12.brain.authority_signature import sign_contract, verify_contract_signature, ALGORITHM

class AuthoritySignatureTests(unittest.TestCase):
    def test_private_signs_public_verifies_without_private_secret(self):
        private=Ed25519PrivateKey.generate()
        raw=private.private_bytes_raw()
        pub=private.public_key().public_bytes_raw()
        contract={"brain_id":"b","generation":1,"fencing_token":2,"lease_id":"l","holder_id":"h","task_id":"t","attempt_id":"a","source_commit":"0"*40,"capability":"windows-server-2025-real-boot","executor":"windows-real-boot-qemu","authority_policy_version":"authority-policy-v1","authority_decision":"AUTHORIZED","authority_signature_algorithm":ALGORITHM}
        sig=sign_contract(contract,base64.b64encode(raw).decode())
        self.assertTrue(verify_contract_signature(contract,sig,base64.b64encode(pub).decode()))
        contract["task_id"]="tampered"
        self.assertFalse(verify_contract_signature(contract,sig,base64.b64encode(pub).decode()))

if __name__=="__main__": unittest.main()
