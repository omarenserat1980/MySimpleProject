#!/usr/bin/env python3
"""Decrypt and verify a Brain email recovery package."""
from __future__ import annotations
import argparse, getpass, hashlib, os, struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pathlib import Path

MAGIC=b"EBREC2\\0"; SALT_LEN=32; NONCE_LEN=12; KEY_LEN=32; ITERATIONS=600_000

def derive(password: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password, salt, 600_000, dklen=KEY_LEN)

def stream(key: bytes, nonce: bytes, n: int):
    out=bytearray(); i=0
    while len(out)<n:
        out.extend(hmac.new(key, nonce+struct.pack(">Q",i), hashlib.sha256).digest())
        i+=1
    return bytes(out[:n])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args=ap.parse_args()
    raw=args.input.read_bytes()
    if len(raw)<len(MAGIC)+4+SALT_LEN+NONCE_LEN+8+32 or not raw.startswith(MAGIC):
        raise SystemExit("INVALID_RECOVERY_PACKAGE")
    pos=len(MAGIC)
    iterations=struct.unpack(">I",raw[pos:pos+4])[0]; pos+=4
    if iterations!=600_000: raise SystemExit("UNSUPPORTED_KDF")
    salt=raw[pos:pos+SALT_LEN]; pos+=SALT_LEN
    nonce=raw[pos:pos+NONCE_LEN]; pos+=NONCE_LEN
    n=struct.unpack(">Q",raw[pos:pos+8])[0]; pos+=8
    cipher=raw[pos:pos+n]; pos+=n
    tag=raw[pos:pos+32]
    header=raw[:len(MAGIC)+4+SALT_LEN+NONCE_LEN+8]
    pw=os.getenv("BRAIN_RECOVERY_PASSPHRASE") or getpass.getpass("Brain recovery passphrase: ")
    key=derive(pw.encode(),salt)
    expected=hmac.new(key,header+cipher,hashlib.sha256).digest()
    if not hmac.compare_digest(tag,expected): raise SystemExit("AUTHENTICATION_FAILED")
    plain=bytes(a^b for a,b in zip(cipher,stream(key,nonce,n)))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(plain)
    print("OK SHA256="+hashlib.sha256(plain).hexdigest())
if __name__=="__main__":
    main()
