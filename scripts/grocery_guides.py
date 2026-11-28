"""Publish shopping-size comparisons for staple foods from the existing StatCan snapshot."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from html import escape
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

BASE = "https://coolcode.ca/priceatlas/"
METHODOLOGY = "https://www150.statcan.gc.ca/n1/pub/62f0014m/62f0014m2022007-eng.htm"
CPI = "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401"
CENT = Decimal(".01")

# Keep the canonical route stable. Each conversion explicitly names its source package
# and shopping quantity, so overlapping milk sizes are never treated as one series.
# (published product, route, title, size to compare, conversion multiplier)
STAPLES = (
    ("Eggs, 1 dozen", "eggs", "Eggs", "18 eggs", Decimal(18) / 12),
    ("Milk, 4 litres", "milk-4-litres", "Milk (4 L)", "1 litre", Decimal(1) / 4),
    ("Milk, 2 litres", "milk-2-litres", "Milk (2 L)", "1 litre", Decimal(1) / 2),
    ("Butter, 454 grams", "butter", "Butter", "100 g", Decimal(100) / 454),
    ("White bread, 675 grams", "white-bread", "White bread", "100 g", Decimal(100) / 675),
    ("Ground beef, per kilogram", "ground-beef", "Ground beef", "1 lb", Decimal(".45359237")),
    ("Chicken breasts, per kilogram", "chicken-breasts", "Chicken breasts", "1 lb", Decimal(".45359237")),
    ("Roasted or ground coffee, 340 grams", "coffee", "Roasted or ground coffee", "100 g", Decimal(100) / 340),
    ("Block cheese, 500 grams", "block-cheese", "Block cheese", "100 g", Decimal(1) / 5),
    ("Potatoes, 4.54 kilograms", "potatoes-10-lb-bag", "Bagged potatoes", "1 kilogram", Decimal(1) / Decimal("4.54")),
    ("Bananas, per kilogram", "bananas", "Bananas", "1 lb", Decimal(".45359237")),
    ("White rice, 2 kilograms", "white-rice", "White rice", "1 kilogram", Decimal(1) / 2),
    ("Infant formula, 900 grams", "infant-formula", "Infant formula", "100 g", Decimal(1) / 9),
)


def amount(value):
    return f"${Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP):,.2f}"


def month(key):
    return date.fromisoformat(key + "-01").strftime("%B %Y")


def link(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def place(snapshot, code):
    return snapshot["coverage"][code]["source_name"]


def path_for(slug, name, code):
    if code == "CA":
        return f"records/{slug}/"
    city_or_province = name.split(",")[0]
    return f"records/{slug}/{city_or_province.lower().replace(' ', '-')}/"


def record_shell(title, description, path, content):
    url = BASE + path
    return f"""<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · Canadian Price Atlas</title><meta name="description" content="{escape(description, quote=True)}">
<link rel="canonical" href="{url}"><meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(description, quote=True)}"><meta property="og:url" content="{url}">
<link rel="stylesheet" href="/priceatlas/style.css"><script defer src="/assets/tool-metrics.js" referrerpolicy="no-referrer"></script></head>
<body><header class="dark"><nav class="wrap" aria-label="Main"><a class="brand" href="/priceatlas/">Canadian Price Atlas</a>
<a href="/priceatlas/records/">Grocery price guides</a><a href="/">CoolCode.ca</a></nav></header>
<main class="wrap price-guide">{content}</main></body></html>"""


def detail(snapshot, product, spec, code, paths):
    _, _, label, quantity, ratio = spec
    series = product["regions"][code]
    latest = max(index for index, v in enumerate(series) if v is not None)
    key = snapshot["months"][latest]
    period = month(key)
    name = place(snapshot, code)
    price = series[latest]
    size = product["name"].split(", ", 1)[1]
    basis = size if size.startswith("per ") else "for " + size
    title = f"Price of {label[:1].lower() + label[1:]} in {name}"
    lead = f"{amount(price)} {basis} was the average retail price in {name} in {period}."
    content = f'<h1>{escape(title)}</h1><p class="guide-answer"><strong>{amount(price)}</strong> {escape(basis)} · {escape(period)} · CAD</p>'
    content += f'<p>Statistics Canada’s monthly average for {escape(product["name"])} in {escape(name)}.</p>'
    if key != snapshot["months"][-1]:
        content += f'<p>The latest table month is {month(snapshot["months"][-1])}. The last price published for this item here is from {period}.</p>'
    if snapshot["coverage"][code]["scope"] == "city":
        content += f'<p>This figure covers the city of {escape(name.split(",")[0])} only.</p>'

    equivalent = amount(Decimal(str(price)) * ratio)
    areas = code + ",CA" if code != "CA" else "CA,BC,ON,NS"
    areas = ",".join(a for a in areas.split(",") if snapshot["coverage"][a]["status"] == "published")
    query = urlencode({"product": product["id"], "areas": areas, "from": snapshot["months"][max(0, latest - 35)], "through": key})
    content += (f'<section class="guide-card"><h2>Compare a shelf price</h2><p>At this average, '
                f'<strong>{escape(quantity)} works out to {equivalent}</strong>. Compare a shelf or flyer price for the same quantity. '
                'A different package size or brand can have a different unit price.</p>'
                f'<p>{link("/priceatlas/?" + query, "Open this item in the price chart and basket")}</p></section>')

    if code == "CA":
        rows = []
        for area, route in paths.items():
            if area == "CA":
                continue
            value = product["regions"][area][latest]
            rows.append(f'<tr><th scope="row">{link("/priceatlas/" + route, place(snapshot, area))}</th>'
                        f'<td>{amount(value) if value is not None else "Unpublished"}</td></tr>')
        if rows:
            content += (f'<section><h2>Compare places in {period}</h2><p>These averages use the same published package. '
                        'The brands and retailers represented can vary by place.</p><table><thead><tr><th>Place</th>'
                        '<th>Average (CAD)</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></section>')
    else:
        national = product["regions"]["CA"][latest]
        if national is not None:
            content += (f'<section><h2>How does the Canadian average compare?</h2><p>In {period}, '
                        f'the Canadian average {escape(basis)} was <strong>{amount(national)}</strong>, '
                        f'compared with <strong>{amount(price)}</strong> in {escape(name)}. Brands and retailers can differ between places.</p></section>')
        if "CA" in paths:
            content += f'<p>{link("/priceatlas/" + paths["CA"], "Compare this item across Canada")}</p>'

    rows = []
    for index in range(latest, max(-1, latest - 12), -1):
        value = series[index]
        rows.append(f'<tr><th scope="row">{month(snapshot["months"][index])}</th><td>{amount(value) if value is not None else "Unpublished"}</td></tr>')
    content += ('<section><h2>Recent published averages</h2><p>Use these monthly amounts for shopping context. '
                f'Brand mix, promotions and package sizes can change. Use the {link(CPI, "Consumer Price Index")} to measure inflation.</p>'
                '<table><thead><tr><th>Month</th><th>Average (CAD)</th></tr></thead><tbody>'
                + "".join(rows) + '</tbody></table></section>')
    content += (f'<section><h2>Source and coverage</h2><p>{link(snapshot["source"], "Statistics Canada table 18-10-0245-01")}, '
                f'vector {escape(product["vectors"][code])}. Source snapshot prepared {escape(snapshot["built"][:10])} UTC. '
                f'{link(METHODOLOGY, "How Statistics Canada calculates the average")}.</p>'
                f'<p>{link("/priceatlas/records/", "Browse more grocery prices")} · '
                f'{link("/pantryprices/", "Compare grocery baskets in Pantry Prices")}</p></section>')
    return record_shell(title, lead, paths[code], content)


def write_guides(stage, snapshot):
    products = {product["name"]: product for product in snapshot["products"]}
    locations = []
    directory = []
    mapping = {}

    def publish(path, markup):
        folder = stage / path
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(markup, encoding="utf-8")
        locations.append(BASE + path)

    for spec in STAPLES:
        source_name, slug, label, _, _ = spec
        product = products.get(source_name)
        if not product:
            continue
        paths = {code: path_for(slug, place(snapshot, code), code)
                 for code, prices in product["regions"].items()
                 if snapshot["coverage"][code]["status"] == "published" and any(value is not None for value in prices)}
        if not paths:
            continue
        mapping[product["id"]] = paths
        for code, path in paths.items():
            publish(path, detail(snapshot, product, spec, code, paths))
        links = [link("/priceatlas/" + path, place(snapshot, code)) for code, path in paths.items()]
        directory.append(f'<section id="{slug}"><h2>{escape(source_name)}</h2><ul class="guide-areas">'
                         + "".join(f'<li>{item}</li>' for item in links) + '</ul></section>')

    if directory:
        title = "Grocery prices by product and province"
        description = "Find a Canadian grocery staple, check the price of its published package in your area, and compare it with the price on a shelf or flyer."
        jump = [link("#" + item[1], item[2]) for item in STAPLES if products.get(item[0], {}).get("id") in mapping]
        content = (f'<h1>{title}</h1><p>{description}</p><ul class="guide-areas">'
                   + "".join(f'<li>{item}</li>' for item in jump) + '</ul>' + "".join(directory)
                   + f'<p>{link(snapshot["source"], "Source: Statistics Canada monthly retail prices")}</p>')
        publish("records/", record_shell(title, description, "records/", content))
        sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for url in sorted(locations):
            ET.SubElement(ET.SubElement(sitemap, "url"), "loc").text = url
        ET.ElementTree(sitemap).write(stage / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    return mapping
