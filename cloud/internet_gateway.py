import os
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

BLOCK_PRIVATE = os.getenv("BRAIN_BLOCK_PRIVATE_NETWORKS", "1") != "0"
TIMEOUT = float(os.getenv("BRAIN_HTTP_TIMEOUT", "30"))

def _is_public_host(host: str) -> bool:
    if not BLOCK_PRIVATE:
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return False
    return True

def fetch(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only http/https public URLs are allowed")
    if not _is_public_host(parsed.hostname):
        raise ValueError("Private/local network targets are blocked")
    headers = {"User-Agent": os.getenv("BRAIN_USER_AGENT", "ElectronicBrain/1.0")}
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        return {
            "url": str(response.url),
            "status": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "text": response.text[:2_000_000],
        }
