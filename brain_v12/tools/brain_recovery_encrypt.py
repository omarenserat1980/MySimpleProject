#!/usr/bin/env python3
"""Encrypt a Brain recovery snapshot using AES-256-GCM."""
from __future__ import annotations
import argparse, getpass, hashlib, json, os, struct, secrets
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC=b"EBREC2\0"
SALT_LEN=32
NONCE_LEN=12
KEY_LEN=32
ITERATIONS=600_000

def derive(password: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password, salt, ITERATIONS, dklen=KEY_LEN)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args=ap.parse_args()
    if not args.input.is_file(): raise SystemExit("INPUT_NOT_FOUND")
    if args.input.resolve()==args.output.resolve(): raise SystemExit("OUTPUT_MUST_DIFFER")
    pw=os.getenv("BRAIN_RECOVERY_PASSPHRASE") or getpass.getpass("Brain recovery passphrase: ")
    if not pw: raise SystemExit("PASSPHRASE_REQUIRED")
    salt=secrets.token_bytes(SALT_LEN)
    nonce=secrets.token_bytes(NONCE_LEN)
    key=derive(pw.encode(),salt)
    plain=args.input.read_bytes()
    header=MAGIC+struct.pack(">I",ITERATIONS)+salt+nonce+struct.pack(">Q",len(plain))
    cipher=AESGCM(key).encrypt(nonce,plain,header)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(header+cipher)
    result={"kdf":"PBKDF2-HMAC-SHA256","format":"brain-email-recovery-v2","cipher":"AES-256-GCM","iterations":ITERATIONS,"plaintext_sha256":hashlib.sha256(plain).hexdigest(),"encrypted_bytes":args.output.stat().st_size,"secrets_included":False,"passphrase_stored":False}
    meta=args.output.with_suffix(args.output.suffix+".manifest.json")
    meta.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"ok":True,"encrypted":str(args.output),"manifest":str(meta)},ensure_ascii=False))
if __name__=="__main__": main()
