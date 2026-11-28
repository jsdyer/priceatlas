from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from grocery_guides import amount, write_guides


class GroceryGuidesTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "built": "2026-11-28T00:00:00+00:00",
            "source": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810024501",
            "months": ["2026-01", "2026-02", "2026-03"],
            "coverage": {
                code: {"source_name": name, "scope": scope, "status": "published"}
                for code, name, scope in [("CA", "Canada", "national"), ("ON", "Ontario", "province"),
                                           ("YT", "Whitehorse, Yukon", "city"), ("NT", "Yellowknife, Northwest Territories", "city"),
                                           ("BC", "British Columbia", "province"), ("NS", "Nova Scotia", "province")]
            },
            "products": [{"id": "v123", "name": "Eggs, 1 dozen",
                          "regions": {"CA": [None, 4.90, 5.00], "YT": [5.00, 5.03, None],
                                      "ON": [4.50, None, 4.80], "NT": [None] * 3},
                          "vectors": {"YT": "v321", "CA": "v123", "ON": "v333"}}]
        }

    def test_dated_package_conversion_and_actual_same_month(self):
        with TemporaryDirectory() as temp:
            base = Path(temp)
            mapping = write_guides(base, self.snapshot)
            self.assertEqual(set(mapping["v123"]), {"CA", "YT", "ON"})
            yt = (base / "records/eggs/whitehorse/index.html").read_text()
            self.assertIn("18 eggs works out to $7.55", yt)
            self.assertIn("city of Whitehorse only", yt)
            self.assertIn("last price published for this item here is from February 2026", yt)
            self.assertIn("<strong>$4.90</strong>", yt)
            self.assertNotIn("<strong>$5.00</strong>", yt)
            self.assertIn("through=2026-02", yt)
            self.assertIn("v321", yt)
            overview = (base / "records/eggs/index.html").read_text()
            self.assertIn("Whitehorse, Yukon</a></th><td>Unpublished", overview)
            self.assertNotIn("Yellowknife", overview)
            sitemap = ET.parse(base / "sitemap.xml")
            urls = [loc.text for loc in sitemap.findall(".//{*}loc")]
            self.assertEqual(len(urls), 4)
            self.assertEqual(len(set(urls)), len(urls))
            for url in urls:
                page = (base / url.split("/priceatlas/")[1] / "index.html").read_text()
                self.assertIn(f'rel="canonical" href="{url}"', page)

    def test_offline_archive_without_featured_products(self):
        self.snapshot["products"][0]["name"] = "Another packaged staple"
        with TemporaryDirectory() as temp:
            base = Path(temp)
            self.assertEqual(write_guides(base, self.snapshot), {})
            self.assertFalse((base / "sitemap.xml").exists())

    def test_cent_rounding(self):
        self.assertEqual(amount("1.005"), "$1.01")
