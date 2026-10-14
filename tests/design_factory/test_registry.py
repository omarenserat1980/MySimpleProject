import unittest
from brain_v12.design_factory.registry import load_registry,audit_prompt_files
class RegistryTests(unittest.TestCase):
 def test_registry_has_unique_prompt_ids(self):
  ids=[x["id"] for x in load_registry()["prompts"]]
  self.assertEqual(len(ids),len(set(ids)))
  self.assertEqual(ids,[f"{i:02d}" for i in range(16)])
 def test_all_registered_prompt_files_exist(self):
  result=audit_prompt_files()
  self.assertEqual(result["status"],"PASS",result["missing"])
  self.assertEqual(result["missing"],[])
  self.assertIn("does not prove",result["meaning"])
if __name__=="__main__": unittest.main()
