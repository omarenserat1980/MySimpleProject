import unittest

from brain_v12.brain.capability_catalog import build_default_fabric, catalog_snapshot
from brain_v12.brain.autonomy_policy import AutonomyPolicy


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

    def test_external_side_effect_requires_permissions_and_policy(self):
        required = {"external_publish", "youtube.upload"}
        default_fabric = build_default_fabric(include_offline=True)
        self.assertEqual(default_fabric.plan("publish.youtube"), [])
        # Permissions alone must not bypass the default external-side-effect deny.
        self.assertEqual(default_fabric.plan("publish.youtube", required), [])

        authorized_fabric = build_default_fabric(
            include_offline=True,
            autonomy_policy=AutonomyPolicy(allow_external_side_effects=True),
        )
        self.assertEqual(
            [x.executor_id for x in authorized_fabric.plan("publish.youtube", required)],
            ["youtube-publisher"],
        )
        # A permissive policy still cannot replace the executor's explicit permissions.
        self.assertEqual(authorized_fabric.plan("publish.youtube", {"external_publish", "youtube.upload", "admin"}), [])


if __name__ == "__main__":
    unittest.main()
