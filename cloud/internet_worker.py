import json
import os
import time
from internet_gateway import fetch

INTERVAL = int(os.getenv("BRAIN_INTERNET_INTERVAL_SECONDS", "300"))
URLS = [u.strip() for u in os.getenv("BRAIN_PUBLIC_URLS", "").split(",") if u.strip()]

print("BRAIN_INTERNET_GATEWAY=1", flush=True)
print("BRAIN_INTERNET_MODE=public-http", flush=True)

while True:
    for url in URLS:
        try:
            result = fetch(url)
            print(json.dumps({"event":"internet_fetch","result":result}, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"event":"internet_fetch_error","url":url,"error":str(exc)}, ensure_ascii=False), flush=True)
    time.sleep(INTERVAL)
