import unittest

from brain_v12.brain.autonomy_policy import AutonomyPolicy
from brain_v12.brain.capability_catalog import build_default_fabric, catalog_snapshot


class CapabilityCatalogTests(unittest.TestCase):
    def test_catalog_is_provider_independent(self):
        fabric = build_default_fabric()
        ids = [x.executor_id for x in fabric.discover("ai.reasoning")]
        self.assertEqual(ids, ["brain-ai-gateway"])

    def test_unprobed_local_media_is_not_claimed_online(self):
        fabric = build_default_fabric()
        self.assertEqual(fabric.discover("media.render"), [])
        inventory = {x["executor_id"]: x for x in catalog_snapshot()}
        self.assertTrue(inventory["local-ffmpeg"]["metadata"]["requires_probe"])

    def test_external_side_effect_requires_explicit_permissions(self):
        fabric = build_default_fabric(include_offline=True)
        self.assertEqual(fabric.plan("publish.youtube"), [])
        self.assertEqual([x.executor_id for x in fabric.plan("publish.youtube", {"external_publish", "youtube.upload"})], [])
        authorized = build_default_fabric(include_offline=True)
        authorized.autonomy_policy = AutonomyPolicy(allow_external_side_effects=True)
        self.assertEqual([x.executor_id for x in authorized.plan("publish.youtube", {"external_publish", "youtube.upload"})], ["youtube-publisher"])


if __name__ == "__main__":
    unittest.main()
