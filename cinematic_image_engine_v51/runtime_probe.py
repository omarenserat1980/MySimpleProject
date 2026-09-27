#!/usr/bin/env python3
from __future__ import annotations
import json
from .local_runtime import discover_runtime, device_profile

def main():
    print(json.dumps({
        "device": device_profile(),
        "image_runtimes": discover_runtime(),
        "adapter_env": "EB_IMAGE_ADAPTER"
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
