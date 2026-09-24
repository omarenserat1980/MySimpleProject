import unittest

from brain.live_opportunity_researcher import LiveOpportunityResearcher


class LiveOpportunityResearcherTests(unittest.TestCase):
    def test_sources_include_primary_freelance_channels(self):
        names = {name for name, _ in LiveOpportunityResearcher.SOURCES}
        self.assertIn("Mostaql Programming", names)
        self.assertIn("Mostaql Python", names)
        self.assertIn("Mostaql API", names)
        self.assertIn("Upwork WhatsApp API", names)

    def test_extract_accepts_absolute_and_relative_listing_links(self):
        researcher = LiveOpportunityResearcher(None, None)
        html = '''
        <a href="/projects/123">Build Python API</a>
        <a href="https://www.upwork.com/freelance-jobs/apply/x">WhatsApp API integration</a>
        <a href="/privacy">Privacy policy</a>
        '''
        out = researcher._extract("Mostaql Programming", "https://mostaql.com/projects/skill/برمجة", html)
        urls = {item["url"] for item in out}
        self.assertIn("https://mostaql.com/projects/123", urls)
        self.assertIn("https://www.upwork.com/freelance-jobs/apply/x", urls)
        self.assertNotIn("https://mostaql.com/privacy", urls)


if __name__ == "__main__":
    unittest.main()
