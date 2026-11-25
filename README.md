# Canadian Price Atlas

<!-- coolcode:guide -->
Compare all ten provinces and Canada, plus Whitehorse and Yellowknife where monthly prices are published. The northern series cover those cities only; Nunavut is explicitly marked unavailable with a link to its separate survey. Add package quantities to a basket and compare exact endpoint months. Missing prices remain missing, and CSV exports retain Statistics Canada vector identifiers.
<!-- /coolcode:guide -->

[Open the Canadian Price Atlas](https://coolcode.ca/priceatlas/) to explore published monthly prices for selected goods across Canada, all ten provinces, Whitehorse (Yukon) and Yellowknife (Northwest Territories). All thirteen provinces and territories appear in the area list, including an explicit unavailable entry for Nunavut. Search product descriptions, choose the areas and range, chart published package prices, use per-kilogram or per-litre conversions where the source specifies a weight or volume, and index the series to a shared observation month. Dates, products, units and selected areas are shareable in the URL. Use “All published areas” to compare every available series, or pick only the areas you need. Coverage tables show actual first/last observation months and available product counts by area, plus coverage of your selected product. Use the chart’s date slider or open the data table, and download the selected rows with Statistics Canada vector identifiers.

Add products to a basket with package quantities to compare complete totals for selected areas and exact endpoint months. Missing prices are listed, and the basket CSV includes the underlying package observations and vectors. The basket lasts for the current page session.

The chart and exports run against a static JSON snapshot. Price averages describe published products over a month and geographic area. The site labels missing observations, retains published package prices in exports and distinguishes the chart’s units from source units. A package comparison uses the product’s published unit or size, and range comparisons use the first and last month with data in every selected area.

## Geographic coverage

The full [Statistics Canada table 18-10-0245-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810024501) is imported rather than filtering to BC and Nova Scotia. The 2026-11-25 source check contains 110 products over January 2017–September 2026. The product list, dates and area coverage counts are derived from each download.

| Area | Published coverage in this source check |
| --- | --- |
| Canada and all 10 provinces | January 2017–September 2026; 110 products except Newfoundland and Labrador (109) |
| Yukon | Whitehorse only, September 2025–September 2026; 59 products with a published value |
| Northwest Territories | Yellowknife only, September 2025–September 2026; 39 products with a published value (one additional series is entirely missing) |
| Nunavut | No comparable monthly series in this table; shown explicitly as unavailable |

Whitehorse and Yellowknife are **city observations, not territory-wide averages**. Product availability and missing months differ by area. No observations are filled, interpolated or substituted. Package descriptions, prices and vector IDs remain matched; new products and later source months are included automatically. The latest-price panel uses one clearly stated month for every selected area, even when an area has no observation.

The [Nunavut Bureau of Statistics publishes a separate Food Price Survey](https://www.gov.nu.ca/en/nunavummit-kiglisiniartiit-nunavut-bureau-statistics/prices-and-cost-living-statistics), including a revised 2025 baseline. Its survey dates, package/product definitions and community coverage differ, so those figures are linked separately rather than spliced into the monthly series. CPI values are not dollar prices and are not used to fill these gaps. The tool’s optional index is calculated from the selected product’s observed prices; it is not CPI.

## Build

```sh
python3 -m unittest discover -s tests -v
node --test tests/*.test.mjs
python3 scripts/build.py
python3 -m http.server 8080 --directory dist
```

The Python 3.11+ build uses only the standard library and validates the source schema, dates, units and expected coverage before publishing the snapshot. Use `--input FILE` to build from a previously downloaded source ZIP or the original StatCan table CSV. Historical imports keep their original date/product coverage and can omit newer areas; absent areas are shown as unavailable. A normal scheduled download requires all thirteen currently published national/provincial/city areas and fails if an unreviewed geography or incompatible unit appears. Failed collection does not publish a replacement site. Local CSS, modules and snapshot requests share a content version so an updated page cannot reuse an incompatible cached module or dataset. The generated site uses relative paths for the CoolCode GitHub Pages subdirectory.

Browser checks run after the real data build in the Pages workflow. Locally, install `tests/browser-requirements.txt`, then run `CHROMIUM_PATH=/path/to/chrome python3 tests/browser_smoke.py` (or install Playwright’s Chromium). The checks cover all areas, northern missing data, shared-month indexes, basket totals, CSV downloads, shareable filters and the mobile layout.

Adapted from Statistics Canada, [Table 18-10-0245-01, Monthly average retail prices for selected products](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810024501), latest reference periods shown in the tool. This does not constitute an endorsement by Statistics Canada of this product. [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence).

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

The separate schedule guard remains a mitigation, not a scheduling guarantee. The independent [CoolCode refresh watchdog](https://github.com/jsdyer/jsdyer.github.io/blob/main/services/refresh-watchdog/README.md) is maintained in GitHub and uses the generated workflow and freshness registry; do not maintain another target list here. Using it requires installation on a Linux server and GitHub credentials with access to this repository. A generated target does not prove that a private server has adopted it; verify the installed service's report. The guard does not collect data, create dummy commits or change source/check timestamps. Successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->
