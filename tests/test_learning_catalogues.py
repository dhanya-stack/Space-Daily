import datetime as dt
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class LearningCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.discoveries = json.loads((ROOT / "data" / "discoveries.json").read_text(encoding="utf-8"))["discoveries"]
        cls.subjects = json.loads((ROOT / "data" / "learning-paths.json").read_text(encoding="utf-8"))["subjects"]

    def test_discovery_catalogue_has_thirty_unique_reviewed_dates(self):
        self.assertEqual(30, len(self.discoveries))
        dates = [dt.date.fromisoformat(item["date"]) for item in self.discoveries]
        self.assertEqual(30, len(set(dates)))
        self.assertEqual(sorted(dates), dates)
        self.assertEqual(dt.date(2026, 10, 24), dates[0])
        self.assertEqual(dt.date(2026, 11, 22), dates[-1])

    def test_discoveries_have_authoritative_sources_and_consistent_quizzes(self):
        for item in self.discoveries:
            self.assertTrue(item["source"].startswith("https://") and "nasa.gov" in item["source"])
            self.assertGreaterEqual(len(item["answers"]), 2)
            self.assertIn(item["correct"], range(len(item["answers"])))
            self.assertTrue(item["imageLink"].startswith("https://images.nasa.gov/"))

    def test_course_has_three_subjects_fifteen_chapters_and_actual_lessons(self):
        self.assertEqual(3, len(self.subjects))
        chapters = [chapter for subject in self.subjects for chapter in subject["chapters"]]
        lessons = [lesson for chapter in chapters for lesson in chapter["lessons"]]
        self.assertEqual(15, len(chapters))
        self.assertEqual(15, len(lessons))
        for chapter in chapters:
            self.assertTrue(chapter["intro"])
            self.assertTrue(chapter["lessons"])
        for lesson in lessons:
            self.assertTrue(lesson["source"].startswith("https://") and "nasa.gov" in lesson["source"])
            self.assertIn(lesson["correct"], range(len(lesson["answers"])))

    def test_utc_date_rule_handles_leap_day_as_a_normal_sparse_lookup(self):
        by_date = {item["date"]: item for item in self.discoveries}
        self.assertIsNone(by_date.get("2028-02-29"))
        self.assertEqual("earth-rotation", by_date["2026-10-24"]["id"])


if __name__ == "__main__":
    unittest.main()
