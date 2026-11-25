import csv
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import AREAS, GEOGRAPHIES, ROOT, month_range, normalize, unit_size, version_assets

FIELDS = ['REF_DATE', 'GEO', 'Products', 'UOM', 'SCALAR_FACTOR', 'VECTOR', 'VALUE', 'STATUS']


def fixture(codes=None):
    rows = []
    for g, (source, code) in enumerate(GEOGRAPHIES.items()):
        if codes and code not in codes:
            continue
        for product in range(50):
            months = ['2026-08', '2026-09'] if code in {'YT', 'NT'} else month_range('2023-10', '2026-09')
            for month in months:
                rows.append(dict(zip(FIELDS, [month, source, f'Product {product}, 2 litres', 'Dollars', 'units', f'v{1000 + 100 * g + product}', str(2 + g + product / 10), ''])))
    return rows


def table(rows):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    out.seek(0)
    return csv.DictReader(out)


class NormalizationTests(unittest.TestCase):
    def test_all_jurisdictions_and_honest_city_coverage(self):
        data = normalize(table(fixture()))
        self.assertEqual(set(data['groups']), set(AREAS))
        self.assertEqual(len(data['months']), 36)
        self.assertEqual(data['coverage']['YT']['scope'], 'city')
        self.assertEqual(data['coverage']['NT']['source_name'], 'Yellowknife, Northwest Territories')
        self.assertEqual(data['coverage']['YT']['first'], '2026-08')
        self.assertEqual(data['coverage']['NU']['status'], 'unavailable')
        product = data['products'][0]
        self.assertEqual(product['regions']['YT'][:34], [None] * 34)
        self.assertEqual(product['regions']['NU'], [None] * 36)
        self.assertNotIn('NU', product['vectors'])
        self.assertEqual(product['id'], 'v1000')
        self.assertEqual(product['unit'], {'quantity': 2, 'unit': 'L'})
        self.assertEqual(product['regions']['ON'][0], 8)

    def test_historical_source_remains_importable_but_is_not_accepted_as_current(self):
        rows = fixture({'CA', 'BC', 'NS'})
        with self.assertRaisesRegex(ValueError, 'missing required'):
            normalize(table(rows))
        data = normalize(table(rows), historical=True)
        self.assertEqual(data['coverage']['ON']['status'], 'unavailable')
        self.assertEqual(data['coverage']['BC']['products'], 50)
        self.assertEqual(data['coverage']['YT']['first'], None)

    def test_suppression_and_absent_products_never_become_zero_or_filled_prices(self):
        rows = fixture()
        for row in rows:
            if row['GEO'] == 'Yellowknife, Northwest Territories' and row['Products'] == 'Product 0, 2 litres':
                row['STATUS'], row['VALUE'] = 'x', '99.99'
        data = normalize(table(rows))
        self.assertEqual(data['coverage']['NT']['products'], 49)
        self.assertTrue(all(value is None for value in data['products'][0]['regions']['NT']))

    def test_unreviewed_geography_duplicate_and_wrong_measure_fail_closed(self):
        for change, message in [({'GEO': 'New territory'}, 'Unreviewed'), ({'UOM': 'Index'}, 'Unexpected measurement'), ({'VALUE': '-1'}, 'Invalid price'), ({'VECTOR': 'incorrect'}, 'Invalid vector')]:
            rows = fixture()
            rows[0].update(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                normalize(table(rows))
        rows = fixture()
        rows.append(rows[0].copy())
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            normalize(table(rows))

    def test_package_units_are_not_guessed(self):
        self.assertEqual(unit_size('Milk, 500 millilitres'), {'quantity': .5, 'unit': 'L'})
        self.assertEqual(unit_size('Apples, per kilogram'), {'quantity': 1, 'unit': 'kg'})
        self.assertIsNone(unit_size('Eggs, 1 dozen'))

    def test_entire_asset_graph_is_versioned_together(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary) / 'site'
            shutil.copytree(ROOT / 'web', stage)
            (stage / 'snapshot.json').write_text('{"test":1}')
            version = version_assets(stage)
            self.assertIn(f'app.mjs?v={version}', (stage / 'index.html').read_text())
            self.assertIn(f'style.css?v={version}', (stage / 'index.html').read_text())
            app = (stage / 'app.mjs').read_text()
            for asset in ['basket.mjs', 'coverage.mjs', 'series.mjs', 'snapshot.json']:
                self.assertIn(f'{asset}?v={version}', app)
            shutil.rmtree(stage)
            shutil.copytree(ROOT / 'web', stage)
            (stage / 'snapshot.json').write_text('{"test":1}')
            self.assertEqual(version_assets(stage), version)
            shutil.rmtree(stage)
            shutil.copytree(ROOT / 'web', stage)
            (stage / 'snapshot.json').write_text('{"test":2}')
            self.assertNotEqual(version_assets(stage), version)


if __name__ == '__main__':
    unittest.main()
