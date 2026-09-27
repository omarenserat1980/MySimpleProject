from __future__ import annotations
import os, platform, shutil
from .local_runtime import device_profile, discover_runtime

class LocalModelRouter:
    def __init__(self, config=None):
        self.config=config or {}

    def device_profile(self):
        return device_profile()

    def choose(self, shot_type, target_resolution):
        role="portrait" if shot_type in ("close-up","extreme close-up") else "environment" if shot_type in ("establishing","wide") else "general"
        for item in self.config.get("models",{}).get(role,[]):
            exe=item.get("executable","")
            path=item.get("path","")
            if (exe and shutil.which(exe)) or (path and os.path.exists(path)):
                return {**item,"role":role}
        runtimes=discover_runtime(self.config)
        if runtimes:
            return {"role":role,"executable":runtimes[0]["executable"],"source":runtimes[0]["source"]}
        return {"role":role,"adapter":"unavailable","device":self.device_profile()}
