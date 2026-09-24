import os
import tempfile
import unittest
from datetime import datetime, timezone

from brain_v12.brain.memory import MemoryStore
from brain_v12.brain.income_engine import IncomeEngine
from brain_v12.brain.render_deploy_monitor import RenderDeployMonitor


class IncomeAndRenderContracts(unittest.TestCase):
    def test_channels_are_not_opportunities(self):
        with tempfile.TemporaryDirectory() as d:
            store=MemoryStore(os.path.join(d,"brain.db")); store.init()
            engine=IncomeEngine(store)
            channels=engine.discover(20)
            self.assertEqual(len(channels),20)
            self.assertEqual(store.income_opportunities(20),[])

    def test_live_listing_requires_fresh_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            store=MemoryStore(os.path.join(d,"brain.db")); store.init()
            engine=IncomeEngine(store)
            now=datetime.now(timezone.utc).isoformat()
            accepted=engine.ingest_live_opportunities([{
                "title":"Real current WordPress project","url":"https://example.com/job/1",
                "source":"test-feed","retrieved_at":now,"requirements":"WordPress","budget":"$30-250"
            }])
            self.assertEqual(len(accepted),1)
            self.assertEqual(store.income_opportunities(10)[0]["data"]["source_kind"],"LIVE_OPPORTUNITY")

    def test_render_monitor_exposes_public_poll(self):
        monitor=RenderDeployMonitor(MemoryStore(":memory:"))
        self.assertTrue(hasattr(monitor,"poll_public_once"))


if __name__=="__main__": unittest.main()
