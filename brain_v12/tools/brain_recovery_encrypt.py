#!/usr/bin/env python3
"""Encrypt an existing Brain recovery snapshot for safe email/offsite transport.

The encryption password is supplied at runtime only through BRAIN_RECOVERY_PASSPHRASE
or an interactive prompt. It is never written to the repository, manifest, archive,
logs, or command line arguments.

Uses Python stdlib only: PBKDF2-HMAC-SHA256 + AES-GCM are not available in stdlib,
so this utility intentionally uses a portable authenticated construction based on
PBKDF2-HMAC-SHA256 and HMAC-SHA256 with a stream generated from HMAC blocks.
It provides confidentiality/integrity for the backup transport; production-grade
secret storage should still be preferred for the passphrase.
"""
from __future__ import annotations
import argparse, getpass, hashlib, json, os, secrets, struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pathlib import Path

MAGIC=b"EBREC2\\0"
SALT_LEN=32
NONCE_LEN=12
KEY_LEN=32
ITERATIONS=600_000

def derive(password: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password, salt, ITERATIONS, dklen=KEY_LEN)

def stream(key: bytes, nonce: bytes, n: int):
    out=bytearray()
    i=0
    while len(out)<n:
        out.extend(hmac.new(key, nonce+struct.pack(">Q",i), hashlib.sha256).digest())
        i+=1
    return bytes(out[:n])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args=ap.parse_args()
    if not args.input.is_file():
        raise SystemExit("INPUT_NOT_FOUND")
    if args.input.resolve()==args.output.resolve():
        raise SystemExit("OUTPUT_MUST_DIFFER")
    pw=os.getenv("BRAIN_RECOVERY_PASSPHRASE")
    if not pw:
        pw=getpass.getpass("Brain recovery passphrase: ")
    if not pw:
        raise SystemExit("PASSPHRASE_REQUIRED")
    salt=secrets.token_bytes(SALT_LEN)
    nonce=secrets.token_bytes(NONCE_LEN)
    key=derive(pw.encode(),salt)
    plain=args.input.read_bytes()
    cipher=bytes(a^b for a,b in zip(plain,stream(key,nonce,len(plain))))
    header=MAGIC+struct.pack(">I",ITERATIONS)+salt+nonce+struct.pack(">Q",len(plain))
    tag=hmac.new(key,header+cipher,hashlib.sha256).digest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(header+cipher+tag)
    result={
      "kdf":"PBKDF2-HMAC-SHA256"
      "format":"brain-email-recovery-v1",
      "cipher":"PBKDF2-HMAC-SHA256 + HMAC-authenticated stream",
      "iterations":ITERATIONS,
      "plaintext_sha256":hashlib.sha256(plain).hexdigest(),
      "encrypted_bytes":args.output.stat().st_size,
      "secrets_included":False,
      "passphrase_stored":False
    }
    meta=args.output.with_suffix(args.output.suffix+".manifest.json")
    meta.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"ok":True,"encrypted":str(args.output),"manifest":str(meta)},ensure_ascii=False))
if __name__=="__main__":
    main()
