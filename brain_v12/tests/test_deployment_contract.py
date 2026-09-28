import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
WORKFLOW = ROOT.parent / ".github" / "workflows" / "brain-v12.yml"


class DeploymentContractTests(unittest.TestCase):
    def test_app_compiles(self):
        source = APP.read_text(encoding="utf-8")
        ast.parse(source, filename=str(APP))

    def test_cinematic_model_is_defined_before_use(self):
        tree = ast.parse(APP.read_text(encoding="utf-8"))
        positions = {}
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "CinematicReleaseIn":
                positions["class"] = node.lineno
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "youtube_cinematic_validate":
                positions["function"] = node.lineno
        self.assertIn("class", positions)
        self.assertIn("function", positions)
        self.assertLess(positions["class"], positions["function"])

    def test_json_response_is_imported(self):
        source = APP.read_text(encoding="utf-8")
        self.assertIn("from fastapi.responses import JSONResponse", source)

    def test_v14_contract_is_aligned(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('actions/checkout@v5', workflow)
        self.assertIn('actions/setup-python@v6', workflow)
        self.assertIn('python -m compileall -q brain_v12', workflow)
        self.assertNotIn('render.yaml', workflow)
        self.assertNotIn('onrender.com', workflow)

    def test_workflow_runs_compile_check(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python -m compileall -q brain_v12", workflow)


if __name__ == "__main__":
    unittest.main()
