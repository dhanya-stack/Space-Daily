import unittest
from unittest.mock import patch

import refresh_content


class FakeHeaders:
    def get_content_type(self):
        return "image/jpeg"


class FakeResponse:
    headers = FakeHeaders()
    def __enter__(self): return self
    def __exit__(self, *_args): return False


class RefreshContentTests(unittest.TestCase):
    def setUp(self):
        refresh_content._IMAGE_VALIDATION_CACHE.clear()

    def test_normalise_image_url_allows_only_https_nasa_hosts_and_encodes_paths(self):
        self.assertIsNone(refresh_content.normalise_image_url("https://example.test/image.jpg"))
        self.assertIsNone(refresh_content.normalise_image_url("http://images.nasa.gov/image.jpg"))
        self.assertEqual(
            "https://images-assets.nasa.gov/image/Moon%20image/thumb.jpg",
            refresh_content.normalise_image_url("https://images-assets.nasa.gov/image/Moon image/thumb.jpg"),
        )

    def test_valid_image_url_requires_an_image_content_type(self):
        url = "https://images-assets.nasa.gov/image/PIA04921/PIA04921~thumb.jpg"
        with patch("refresh_content.urllib.request.urlopen", return_value=FakeResponse()) as open_url:
            self.assertEqual(url, refresh_content.valid_image_url(url))
        self.assertEqual(1, open_url.call_count)

    def test_gallery_refresh_drops_unvalidated_preview_urls(self):
        payload = {"collection": {"items": [{"data": [{"title": "Test image", "nasa_id": "TEST 1", "center": "NASA"}], "links": [{"rel": "preview", "href": "https://images-assets.nasa.gov/image/TEST%201/TEST%201~thumb.jpg"}]}]}}
        with patch("refresh_content.get", return_value=__import__("json").dumps(payload).encode()), patch("refresh_content.valid_image_url", return_value=None):
            self.assertEqual([], refresh_content.images("moon"))

    def test_refresh_keeps_previous_image_when_new_metadata_has_none(self):
        previous = [{"link": "https://www.nasa.gov/story/", "image": "https://images-assets.nasa.gov/image/PIA04921/PIA04921~thumb.jpg"}]
        fresh = [{"link": "https://www.nasa.gov/story/", "title": "Updated story"}]
        result = refresh_content.retain_last_valid_images(fresh, previous)
        self.assertEqual(previous[0]["image"], result[0]["image"])


if __name__ == "__main__":
    unittest.main()
