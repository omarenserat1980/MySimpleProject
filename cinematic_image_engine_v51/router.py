from __future__ import annotations
import os, platform, shutil

class LocalModelRouter:
    def __init__(self, config=None):
        self.config=config or {}
    def device_profile(self):
        try: ram=int(os.sysconf("SC_PAGE_SIZE")*os.sysconf("SC_PHYS_PAGES")/1024/1024)
        except Exception: ram=0
        try: free=int(shutil.disk_usage(".").free/1024/1024)
        except Exception: free=0
        return {"ram_mb":ram,"gpu":os.environ.get("EB_GPU","unknown"),
                "npu":os.environ.get("EB_NPU","unknown"),"storage_free_mb":free,
                "platform":platform.platform()}
    def choose(self, shot_type, target_resolution):
        role="portrait" if shot_type in ("close-up","extreme close-up") else "environment" if shot_type in ("establishing","wide") else "general"
        for item in self.config.get("models",{}).get(role,[]):
            if shutil.which(item.get("executable","")) or os.path.exists(item.get("path","")):
                return {**item,"role":role}
        return {"role":role,"adapter":"stub","device":self.device_profile()}
