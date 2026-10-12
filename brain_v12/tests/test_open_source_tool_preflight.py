import unittest

from brain_v12.tools.open_source_tool_preflight import inspect_tool_availability


class OpenSourceToolPreflightTests(unittest.TestCase):
    def test_preflight_never_enables_execution_install_or_hardware_io(self):
        result = inspect_tool_availability(lambda _name: None)
        self.assertEqual(result["mode"], "path_preflight_only")
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["installation_enabled"])
        self.assertFalse(result["hardware_io_enabled"])

    def test_all_known_tools_are_reported_even_when_missing(self):
        result = inspect_tool_availability(lambda _name: None)
        self.assertEqual(result["summary"]["checked"], 9)
        self.assertEqual(result["summary"]["available"], 0)
        self.assertEqual(result["summary"]["not_found"], 9)
        self.assertTrue(all(item["status"] == "not_found" for item in result["tools"]))

    def test_detects_alternative_executable_name_without_launching_it(self):
        def fake_which(name):
            return "/usr/bin/ollama" if name == "ollama" else None

        result = inspect_tool_availability(fake_which)
        ollama = next(item for item in result["tools"] if item["id"] == "ollama")
        self.assertEqual(ollama["status"], "available")
        self.assertEqual(ollama["resolved_executables"], ["/usr/bin/ollama"])
        self.assertEqual(result["summary"]["available"], 1)


if __name__ == "__main__":
    unittest.main()
