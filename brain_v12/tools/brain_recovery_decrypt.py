#!/usr/bin/env python3
"""Decrypt and authenticate a Brain AES-256-GCM recovery package."""
from __future__ import annotations
import argparse, getpass, hashlib, os, struct
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC=b"EBREC2\0"
SALT_LEN=32
NONCE_LEN=12
KEY_LEN=32
ITERATIONS=600_000
TAG_LEN=16

def derive(password: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password, salt, ITERATIONS, dklen=KEY_LEN)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args=ap.parse_args()
    raw=args.input.read_bytes()
    header_len=len(MAGIC)+4+SALT_LEN+NONCE_LEN+8
    if len(raw)<header_len+TAG_LEN or not raw.startswith(MAGIC): raise SystemExit("INVALID_RECOVERY_PACKAGE")
    pos=len(MAGIC)
    iterations=struct.unpack(">I",raw[pos:pos+4])[0]; pos+=4
    if iterations!=ITERATIONS: raise SystemExit("UNSUPPORTED_KDF")
    salt=raw[pos:pos+SALT_LEN]; pos+=SALT_LEN
    nonce=raw[pos:pos+NONCE_LEN]; pos+=NONCE_LEN
    n=struct.unpack(">Q",raw[pos:pos+8])[0]; pos+=8
    if n>len(raw)-header_len-TAG_LEN: raise SystemExit("INVALID_RECOVERY_PACKAGE")
    cipher=raw[pos:pos+n]
    if len(cipher)!=n+TAG_LEN: raise SystemExit("INVALID_RECOVERY_PACKAGE")
    header=raw[:header_len]
    pw=os.getenv("BRAIN_RECOVERY_PASSPHRASE") or getpass.getpass("Brain recovery passphrase: ")
    if not pw: raise SystemExit("PASSPHRASE_REQUIRED")
    key=derive(pw.encode(),salt)
    try: plain=AESGCM(key).decrypt(nonce,cipher,header)
    except Exception as exc: raise SystemExit("AUTHENTICATION_FAILED") from exc
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(plain)
    print("OK SHA256="+hashlib.sha256(plain).hexdigest())
if __name__=="__main__": main()
