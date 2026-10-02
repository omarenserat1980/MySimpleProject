import tempfile
import unittest
from pathlib import Path
from brain_v12.brain.commerce_api import CommerceOrderIn, CommerceStore
from brain_v12.brain.customer_portal import router as customer_router

class CustomerPortalTests(unittest.TestCase):
    def test_portal_router_builds_and_order_has_portal_slot(self):
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/"commerce.json")
            store=CommerceStore(path)
            order=store.create(CommerceOrderIn(customer_name="Customer",contact="c@example.com",product_id="ai-starter-kit"))
            self.assertIn("portal", order)
            self.assertEqual(order["portal"]["token_hash"], "")
            self.assertIsNotNone(customer_router(path))

if __name__=="__main__":
    unittest.main()
