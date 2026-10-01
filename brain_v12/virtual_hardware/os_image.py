from __future__ import annotations
import hashlib, os
from dataclasses import dataclass

@dataclass(frozen=True)
class OSImage:
    name: str
    version: str
    architecture: str
    media_type: str
    path: str | None = None
    sha256: str | None = None

    def inspect(self) -> dict:
        result={"name":self.name,"version":self.version,"architecture":self.architecture,
                "media_type":self.media_type,"path":self.path,"sha256":self.sha256}
        if not self.path:
            return {**result,"present":False,"verified":False,"status":"PATH_NOT_CONFIGURED"}
        if not os.path.isfile(self.path):
            return {**result,"present":False,"verified":False,"status":"IMAGE_NOT_FOUND"}
        actual=hashlib.sha256()
        with open(self.path,"rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""): actual.update(chunk)
        digest=actual.hexdigest()
        verified=(self.sha256 is None or digest.lower()==self.sha256.lower())
        return {**result,"present":True,"verified":verified,"status":"VERIFIED" if verified else "SHA256_MISMATCH",
                "actual_sha256":digest,"size_bytes":os.path.getsize(self.path)}

def windows_server_2025_image(path: str | None = None, sha256: str | None = None) -> OSImage:
    return OSImage("Windows Server", "2025", "x86_64", "ISO_OR_VHD", path, sha256)
