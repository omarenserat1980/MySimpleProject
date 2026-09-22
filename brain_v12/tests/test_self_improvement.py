import unittest

from brain_v12.brain.self_improvement import SelfImprovementEngine


class SelfImprovementTests(unittest.TestCase):
    def test_path_is_allowlisted(self):
        engine=SelfImprovementEngine(repo="")
        with self.assertRaises(ValueError):
            engine.inspect("../README.md")

    def test_status_is_bounded(self):
        engine=SelfImprovementEngine(repo="")
        status=engine.status()
        self.assertFalse(status["enabled"])
        self.assertTrue(status["write_requires_explicit_approval"])
        self.assertFalse(status["chatgpt_session_access"])


if __name__=="__main__":
    unittest.main()
