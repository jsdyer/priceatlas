# Canadian Price Atlas

<!-- coolcode:guide -->
Add products and package quantities to a basket, then compare exact endpoint months across your selected areas. Missing prices are listed rather than filled; exports retain the published package observations and Statistics Canada vector identifiers.
<!-- /coolcode:guide -->

[Open the Canadian Price Atlas](https://coolcode.ca/priceatlas/) to explore published monthly prices for selected goods in British Columbia, Nova Scotia and Canada. Search product descriptions, choose the areas and range, chart published package prices, use per-kilogram or per-litre conversions where the source specifies a weight or volume, and index the series to a shared observation month. Dates and areas are shareable in the URL. Use the chart’s date slider or open the data table, and download the selected rows with Statistics Canada vector identifiers.

Add products to a basket with package quantities to compare complete totals for selected areas and exact endpoint months. Missing prices are listed, and the basket CSV includes the underlying package observations and vectors. The basket lasts for the current page session.

The chart and exports run against a static JSON snapshot. Price averages describe published products over a month and geographic area. The site labels missing observations, retains published package prices in exports and distinguishes the chart’s units from source units. A package comparison uses the product’s published unit or size, and range comparisons use the first and last month with data in every selected area.

## Build

```sh
python3 scripts/build.py
python3 -m http.server 8080 --directory dist
```

The Python 3.11+ build uses only the standard library and validates the source schema, dates, units and expected coverage before publishing the snapshot. Use `--input FILE` to build from a previously downloaded source ZIP or the original StatCan table CSV. The generated site uses relative paths for the CoolCode GitHub Pages subdirectory.

Adapted from Statistics Canada, [Table 18-10-0245-01, Monthly average retail prices for selected products](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810024501), latest reference periods shown in the tool. This does not constitute an endorsement by Statistics Canada of this product. [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence).
