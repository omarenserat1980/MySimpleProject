import unittest

from brain_v12.brain.repair_knowledge import classify, match_rules


class RepairKnowledgeTests(unittest.TestCase):
    def test_ffmpeg_concat_is_bounded(self):
        rule = classify("ffmpeg: concat: Impossible to open part-07.mp4")
        self.assertEqual(rule.rule_id, "FFMPEG_CONCAT_FAILURE")
        self.assertTrue(rule.safe_automatic)

    def test_windows_index_is_discovered(self):
        rule = classify("DISM install.wim Windows Server 2025 Index: 4")
        self.assertEqual(rule.rule_id, "WINDOWS_MEDIA_INDEX")

    def test_windows_guest_failure_blocks_delivery(self):
        rule = classify("WINDOWS_BOOT_VERIFIED=false completion gate rejected")
        self.assertEqual(rule.rule_id, "WINDOWS_GUEST_NOT_VERIFIED")
        self.assertFalse(rule.safe_automatic)

    def test_unknown_failure_never_mutates(self):
        rule = classify("random exception in an unknown module")
        self.assertEqual(rule.rule_id, "UNKNOWN_FAILURE")
        self.assertFalse(rule.safe_automatic)

    def test_multiple_matches_are_available_for_auditing(self):
        matches = match_rules("ffmpeg: No such file or directory")
        self.assertTrue(any(r.rule_id == "FFMPEG_MISSING_INPUT" for r in matches))


if __name__ == "__main__":
    unittest.main()
