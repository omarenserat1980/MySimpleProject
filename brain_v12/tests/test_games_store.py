import unittest
from brain_v12.brain.games_store import CATALOG, catalog, sellable_offers

class GamesStoreContractTests(unittest.TestCase):
    def test_catalog_contains_real_discovery_records(self):
        self.assertGreaterEqual(len(CATALOG), 3)
        for game in catalog():
            self.assertTrue(game["title"])
            self.assertIn(game["platform"], {"PS5", "PC", "Xbox", "Switch"})
            self.assertTrue(game["official_url"])

    def test_unlicensed_games_are_not_sellable_by_brain(self):
        self.assertEqual(sellable_offers(), [])
        for game in catalog():
            self.assertFalse(game["sellable_by_brain"])

if __name__ == "__main__":
    unittest.main()
