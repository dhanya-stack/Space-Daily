import datetime as dt
import json
import os
import pathlib
import unittest
from unittest.mock import patch

import newsletter


class NewsletterTests(unittest.TestCase):
    def setUp(self):
        latest = json.loads((pathlib.Path(__file__).resolve().parents[1] / "data" / "latest.json").read_text(encoding="utf-8"))
        self.issue_date = dt.datetime.fromisoformat(latest["updated"].replace("Z", "+00:00")).date()

    def test_daily_content_uses_three_distinct_non_apod_articles(self):
        content, reason = newsletter.content_for("daily", self.issue_date)
        self.assertIsNone(reason)
        self.assertEqual(3, len(content["articles"]))
        self.assertEqual(3, len({article["link"].rstrip("/") for article in content["articles"]}))
        self.assertTrue(all(not article["title"].lower().startswith("apod:") for article in content["articles"]))

    def test_preview_contains_sources_credit_and_unsubscribe(self):
        content, reason = newsletter.content_for("daily", self.issue_date)
        self.assertIsNone(reason)
        rendered = newsletter.render_html(content, "https://example.test")
        self.assertIn("{{ unsubscribe_url }}", rendered)
        self.assertIn("Image credit:", rendered)
        self.assertIn("Read the NASA source", rendered)

    def test_stale_cache_skips_delivery(self):
        original = newsletter.load_json
        def stale(path, fallback):
            result = original(path, fallback)
            if path.name == "latest.json":
                result = dict(result)
                result["updated"] = "2000-01-01T00:00:00+00:00"
            return result
        newsletter.load_json = stale
        try:
            content, reason = newsletter.content_for("daily", self.issue_date)
        finally:
            newsletter.load_json = original
        self.assertIsNone(content)
        self.assertIn("not successfully refreshed", reason)

    def test_production_gate_is_closed_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(newsletter.NewsletterError):
                newsletter.approved("NEWSLETTER_PRODUCTION_ENABLED", "I_APPROVE_PRODUCTION_SENDING")

    def test_test_audience_requires_the_exact_named_tag_and_one_active_recipient(self):
        tags = {"Space Daily Test": 99, "Daily Newsletter": 10, "Weekly Newsletter": 11}
        with patch.object(newsletter, "active_subscriber_count_for_tag", return_value=1) as count:
            result = newsletter.verify_test_audience("not-a-real-key", tags)
        self.assertEqual({"tag_id": 99, "active_subscriber_count": 1}, result)
        count.assert_called_once_with("not-a-real-key", 99)

    def test_test_audience_blocks_multiple_or_production_recipients(self):
        tags = {"Space Daily Test": 99, "Daily Newsletter": 10, "Weekly Newsletter": 11}
        with patch.object(newsletter, "active_subscriber_count_for_tag", return_value=2):
            with self.assertRaisesRegex(newsletter.NewsletterError, "exactly one"):
                newsletter.verify_test_audience("not-a-real-key", tags)
        with self.assertRaisesRegex(newsletter.NewsletterError, "conflicts"):
            newsletter.verify_test_audience("not-a-real-key", {"Space Daily Test": 10, "Daily Newsletter": 10})

    def test_test_sender_must_be_explicit_and_valid(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(newsletter.NewsletterError, "KIT_TEST_SENDER_EMAIL"):
                newsletter.configured_test_sender()
        with patch.dict(os.environ, {"KIT_TEST_SENDER_EMAIL": "newsletter@example.test"}, clear=True):
            self.assertEqual("newsletter@example.test", newsletter.configured_test_sender())

    def test_test_broadcast_supplies_and_confirms_explicit_sender(self):
        content, reason = newsletter.content_for("daily", self.issue_date)
        self.assertIsNone(reason)
        captured = {}
        def fake_request(_method, _path, _key, payload=None):
            captured.update(payload)
            return {"broadcast": {"id": 42, "email_address": "newsletter@example.test"}}
        with patch.object(newsletter, "existing_broadcast", return_value=None), patch.object(newsletter, "kit_request", side_effect=fake_request):
            result = newsletter.create_broadcast(content, "not-a-real-key", 99, "test-send", "https://example.test", "2026-10-23T12:30:00Z", "newsletter@example.test")
        self.assertEqual("scheduled", result["status"])
        self.assertEqual("newsletter@example.test", captured["email_address"])
        self.assertEqual([99], captured["subscriber_filter"][0]["all"][0]["ids"])


if __name__ == "__main__":
    unittest.main()
