import unittest
from unittest.mock import patch

from brain_v12.brain.device_bridge import DeviceBridge

class _Store:
    def device_agents(self):
        return [{"agent_id":"redmi3-01","last_seen":1000}]
    def device_task_create(self,*a): pass
    def device_task_get(self,*a): return {}
    def device_task_counts(self): return {}
    def device_task_claim(self,*a,**k): return None
    def device_task_report(self,*a,**k): return "COMPLETED"

class UnifiedAndroidGateTest(unittest.TestCase):
    def test_android_task_requires_android_executor(self):
        bridge=DeviceBridge(_Store())
        with patch.object(bridge,"enabled",return_value=True), patch("brain_v12.brain.device_bridge.time.time",return_value=1001):
            result=bridge.enqueue("open_app",{"package":"com.android.settings"})
        self.assertEqual(result["status"],"CAPABILITY_WORKER_OFFLINE")

    def test_android_executor_is_selected(self):
        store=_Store()
        store.device_agents=lambda: [{"agent_id":"android-executor-redmi3-01","last_seen":1000}]
        bridge=DeviceBridge(store)
        with patch.object(bridge,"enabled",return_value=True), patch("brain_v12.brain.device_bridge.time.time",return_value=1001):
            self.assertEqual(bridge.authorized_executor_for_task("open_app"),"android-executor-redmi3-01")

if __name__=="__main__":
    unittest.main()
