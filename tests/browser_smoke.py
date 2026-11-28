"""Exercise the real built snapshot at the Pages subpath with all geographies."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    snapshot = json.loads((ROOT / 'dist/snapshot.json').read_text())
    published = [code for code, area in snapshot['coverage'].items() if area['status'] == 'published']
    common = next(row for row in snapshot['products'] if all(row['regions'][code][-1] is not None for code in published))
    screenshots = ROOT / 'browser-checks'
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / 'dist', Path(temporary) / 'priceatlas')
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                opts = {'executable_path': os.environ['CHROMIUM_PATH']} if os.environ.get('CHROMIUM_PATH') else {}
                browser = p.chromium.launch(**opts)
                page = browser.new_page(viewport={'width': 1280, 'height': 1000})
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.route('**/assets/tool-metrics.js', lambda route: route.fulfill(body=''))
                page.goto(f'http://127.0.0.1:{server.server_port}/priceatlas/')
                page.locator('#plot').wait_for(state='visible')
                assert page.locator('h1').inner_text() == 'Compare Canadian grocery prices'
                assert page.locator('#overview-product').inner_text() == 'Eggs, 1 dozen'
                assert page.locator('#overview-values dt').all_text_contents() == [snapshot['groups'][code] for code in snapshot['groups'] if code in {'CA', 'BC', 'NS'}]
                page.goto(f'http://127.0.0.1:{server.server_port}/priceatlas/?product={common["id"]}&areas=CA,ON,AB,YT,NT')
                page.locator('#controls').wait_for(state='visible')
                assert page.locator('[name=area]').count() == 14
                assert page.locator('[name=area]:checked').count() == 5
                assert page.locator('[value=NU]').is_disabled()
                assert 'Nunavut' in page.locator('#areas').inner_text()
                assert page.locator('#plot').is_visible()
                page.locator('#areas-all').click()
                assert page.locator('#legend li').count() == 13
                assert page.locator('#area-coverage tr').count() == 14
                page.locator('#unit').select_option('index')
                assert 'Index' in page.locator('#chart-description').inner_text()
                assert page.locator('#plot').is_visible()
                with page.expect_download() as download:
                    page.locator('#export').click()
                csv = Path(download.value.path()).read_text()
                assert 'Ontario' in csv and 'Whitehorse only' in csv and 'Yellowknife only' in csv
                assert 'StatCan vector' in csv
                page.locator('#unit').select_option('package')
                page.locator('#basket-add').click()
                assert 'Missing observations' in page.locator('#basket-status').inner_text()
                assert 'Whitehorse' in page.locator('#basket-status').inner_text()
                page.screenshot(path=str(screenshots / 'desktop.png'), full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path=str(screenshots / 'mobile.png'), full_page=True)
                # A product with no northern prices must not hide valid Ontario data.
                product = next(row for row in snapshot['products'] if not any(v is not None for v in row['regions']['YT']) and any(v is not None for v in row['regions']['ON']))
                page.goto(f'http://127.0.0.1:{server.server_port}/priceatlas/?product={product["id"]}&areas=ON,YT')
                page.locator('#controls').wait_for(state='visible')
                assert page.locator('#plot').is_visible()
                assert 'No published prices' in page.locator('#status').inner_text()
                assert 'Whitehorse' in page.locator('#status').inner_text()
                page.locator('#unit').select_option('index')
                assert not page.locator('#plot').is_visible()
                assert 'No shared observation' in page.locator('#status').inner_text()
                page.locator('#areas-clear').click()
                assert 'Select at least one area' in page.locator('#status').inner_text()
                page.locator('[value=ON]').check()
                assert page.locator('#plot').is_visible()
                page.reload()
                page.locator('#controls').wait_for(state='visible')
                assert page.locator('[value=ON]').is_checked()
                assert page.locator('[name=area]:checked').count() == 1
                page.locator('#search').fill('no matching grocery product qqqqq')
                assert 'No products match' in page.locator('#status').inner_text()
                base = f'http://127.0.0.1:{server.server_port}/priceatlas/'
                plain = browser.new_context(java_script_enabled=False, viewport={'width': 320, 'height': 640})
                reader = plain.new_page()
                reader.goto(base)
                reader.get_by_role('link', name='Browse grocery price guides').click()
                reader.locator('#eggs').get_by_role('link', name='Ontario', exact=True).click()
                assert reader.locator('h1').inner_text() == 'Price of eggs in Ontario'
                assert '18 eggs' in reader.locator('.guide-card').inner_text()
                assert reader.evaluate('document.documentElement.scrollWidth <= innerWidth')
                chart_url = reader.get_by_role('link', name='Open this item in the price chart and basket').get_attribute('href')
                plain.close()
                page.goto(f'http://127.0.0.1:{server.server_port}' + chart_url)
                page.locator('#price-guide').wait_for(state='visible')
                assert page.locator('#price-guide').get_attribute('href') == './records/eggs/ontario/'
                assert page.locator('[name=area]:checked').count() == 2
                assert page.locator('[value=ON]').is_checked()
                assert not errors, errors
                browser.close()
            print('Browser checks passed: all regions, city labels, missing observations, shared indexes, basket, CSV, URL restore, product search and mobile layout')
        finally:
            server.shutdown()

if __name__ == '__main__':
    main()
