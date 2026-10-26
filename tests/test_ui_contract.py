import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class UiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "styles.css").read_text(encoding="utf-8")
        cls.paths = json.loads((ROOT / "data" / "learning-paths.json").read_text(encoding="utf-8"))["subjects"]

    def test_discovery_controls_do_not_offer_future_entries(self):
        self.assertIn("next.date<=todayUtc()", self.app)
        self.assertIn("$('discoveryDate').max=todayUtc()", self.app)
        self.assertIn("discoveryDate=permittedDate", self.app)

    def test_news_starts_with_five_items_and_has_a_toggle(self):
        self.assertIn("stories.slice(0,5)", self.app)
        self.assertIn('id="newsToggle"', self.html)
        self.assertIn("deduplicatedNews", self.app)

    def test_subject_cards_are_real_hash_links_with_separate_detail_view(self):
        self.assertIn("#learn/${encodeURIComponent(subject.id)}", self.app)
        self.assertIn("window.addEventListener('hashchange',renderLearningRoute)", self.app)
        self.assertIn('id="courseDetail"', self.html)
        self.assertEqual(3, len(self.paths))

    def test_subject_imagery_is_descriptive_and_uses_nasa_hosts(self):
        for subject in self.paths:
            self.assertTrue(subject["image"].startswith("https://images-assets.nasa.gov/"))
            self.assertTrue(subject["imageLink"].startswith("https://images.nasa.gov/"))
            self.assertTrue(subject["imageAlt"])
            self.assertTrue(subject["fallbackImages"])

    def test_compact_gallery_and_hero_rules_are_present(self):
        self.assertIn("grid-template-columns: repeat(4", self.css)
        self.assertIn("aspect-ratio: 4 / 3", self.css)
        self.assertIn("min-height: 100svh", self.css)
        self.assertIn("STScI-01EVT2C45NSH3P4GTPXYY828KC", self.css)
        self.assertIn("w=6000&h=4000&fit=clip", self.css)
        self.assertIn("w=1200&h=1600&fit=clip", self.css)
        self.assertIn("background-position: 56% 50%", self.css)
        self.assertIn("rgba(3, 5, 12, .18)", self.css)

    def test_hero_uses_minimal_menu_navigation_and_keeps_the_newsletter_link(self):
        self.assertIn('<h1>Space Daily</h1>', self.html)
        self.assertIn("veil-nebula-supernova-remnant", self.html)
        self.assertIn("NASA, ESA, Hubble Heritage Project", self.html)
        self.assertIn('href="#newsletter">Newsletter</a>', self.html)
        self.assertIn('aria-label="Open navigation"', self.html)
        self.assertIn(".site-header { height: 76px", self.css)
        self.assertIn(".site-header nav.open { display: grid; }", self.css)
        self.assertIn("Close navigation", self.app)


if __name__ == "__main__":
    unittest.main()
