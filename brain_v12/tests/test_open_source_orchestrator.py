import unittest
from brain_v12.brain.open_source_orchestrator import plan

class OrchestratorTests(unittest.TestCase):
    def test_selects_only_available_backends(self):
        status={"services":[
            {"id":"ollama","health":{"available":True}},
            {"id":"comfyui","health":{"available":False}},
            {"id":"qdrant","health":{"available":False}},
            {"id":"llama_cpp","health":{"available":False}},
        ]}
        result=plan(["local_reasoning","video_generation"],status)
        self.assertEqual(result[0]["selected"]["id"],"ollama")
        self.assertIsNone(result[1]["selected"])

if __name__=="__main__":
    unittest.main()
