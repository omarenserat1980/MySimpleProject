import ast
import unittest
from pathlib import Path


class CloudFabricAppWiringTests(unittest.TestCase):
    def test_cloud_fabric_router_is_imported_and_registered(self):
        app_path = Path(__file__).with_name("app.py")
        tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))

        imported = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "cloud.brain_fabric_api"
            and any(alias.name == "router" and alias.asname == "cloud_fabric_router"
                    for alias in node.names)
            for node in ast.walk(tree)
        )
        registered = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "app"
            and node.func.attr == "include_router"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "cloud_fabric_router"
            for node in ast.walk(tree)
        )

        self.assertTrue(imported, "Cloud Fabric router import is missing")
        self.assertTrue(registered, "Cloud Fabric router is not registered on Brain V14 app")


if __name__ == "__main__":
    unittest.main()
