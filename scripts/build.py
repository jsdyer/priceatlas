"""Create a static regional price snapshot from Statistics Canada table 18-10-0245-01."""
import argparse
from collections import defaultdict
import csv
from datetime import date, datetime, timezone
import io
import json
import math
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://www150.statcan.gc.ca/n1/tbl/csv/18100245-eng.zip"
TABLE = "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810024501"
GEOGRAPHIES = {"Canada": "CA", "British Columbia": "BC", "Nova Scotia": "NS"}
LIMIT = 15 * 1024 * 1024
SIZE = re.compile(r", (?:(per)|(\d+(?:\.\d+)?))\s*(kilograms?|grams?|litres?|millilitres?)$", re.I)
CONVERSIONS = {
    "kilogram": (1, "kg"),
    "gram": (.001, "kg"),
    "litre": (1, "L"),
    "millilitre": (.001, "L"),
}


def fetch():
    request = Request(SOURCE, headers={"User-Agent": "CoolCode Canadian Price Atlas build (https://coolcode.ca/priceatlas/)"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as connection:
                payload = connection.read(LIMIT + 1)
            if len(payload) > LIMIT:
                raise ValueError("Source ZIP exceeded the size limit.")
            return payload
        except (URLError, TimeoutError, OSError) as error:
            if attempt == 2:
                raise RuntimeError(f"Could not fetch the StatCan table: {error}") from error
            time.sleep(2 ** attempt)


def unit_size(name):
    found = SIZE.search(name)
    if not found:
        return None
    _, amount, raw_unit = found.groups()
    multiplier, unit = CONVERSIONS[raw_unit.lower().removesuffix("s")]
    return {"quantity": float(amount or 1) * multiplier, "unit": unit}


def month_range(first, last):
    year, month = map(int, first.split("-"))
    result = []
    while True:
        key = f"{year:04d}-{month:02d}"
        result.append(key)
        if key == last:
            return result
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def normalize(table):
    fields = {"REF_DATE", "GEO", "Products", "UOM", "SCALAR_FACTOR", "VECTOR", "VALUE", "STATUS"}
    if not fields.issubset(table.fieldnames or []):
        raise ValueError("Statistics Canada CSV headers changed.")
    vectors = defaultdict(dict)
    values = defaultdict(lambda: defaultdict(dict))
    groups = set()
    dates = set()
    for row in table:
        geography = GEOGRAPHIES.get(row["GEO"])
        if not geography:
            continue
        month = row["REF_DATE"]
        parsed = date.fromisoformat(month + "-01")
        if parsed.isoformat()[:7] != month or not 2010 <= parsed.year <= datetime.now(timezone.utc).year:
            raise ValueError(f"Invalid observation month: {month}")
        if row["UOM"] != "Dollars" or row["SCALAR_FACTOR"] != "units":
            raise ValueError(f"Unexpected measurement unit: {row['UOM']} ({row['SCALAR_FACTOR']}).")
        name = row["Products"].strip()
        seen = values[name][geography]
        if month in seen:
            raise ValueError(f"Duplicate observation for {name!r}, {geography}, {month}.")
        status = row["STATUS"]
        amount = float(row["VALUE"]) if row["VALUE"] and status not in {"x", "F", "..", "..."} else None
        if amount is not None and (not math.isfinite(amount) or amount <= 0):
            raise ValueError(f"Invalid price for {name!r}, {geography}, {month}.")
        source_id = row["VECTOR"]
        if not re.fullmatch(r"v\d+", source_id):
            raise ValueError(f"Invalid vector: {source_id}.")
        if geography in vectors[name] and vectors[name][geography] != source_id:
            raise ValueError(f"StatCan vector changed for {name!r}, {geography}.")
        vectors[name][geography] = source_id
        seen[month] = round(amount, 2) if amount is not None else None
        dates.add(month)
        if amount is not None:
            groups.add(geography)
    if groups != set(GEOGRAPHIES.values()) or len(dates) < 36 or len(values) < 50:
        raise ValueError("Snapshot is smaller than expected.")
    axis = month_range(min(dates), max(dates))
    return {
        "source": TABLE,
        "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "months": axis,
        "groups": {code: name for name, code in GEOGRAPHIES.items()},
        "products": [
            {
                "id": vectors[name].get("CA", next(iter(vectors[name].values()))),
                "name": name,
                "unit": unit_size(name),
                "vectors": vectors[name],
                "regions": {
                    code: [values[name][code].get(month) for month in axis] for code in GEOGRAPHIES.values()
                },
            }
            for name in sorted(values, key=str.casefold)
            if any(any(value is not None for value in series.values()) for series in values[name].values())
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Use a saved StatCan source ZIP or uncompressed table CSV.")
    args = parser.parse_args()
    if args.input and args.input.suffix.lower() == ".csv":
        with args.input.open(encoding="utf-8-sig", newline="") as source:
            snapshot = normalize(csv.DictReader(source))
    else:
        payload = args.input.read_bytes() if args.input else fetch()
        with ZipFile(io.BytesIO(payload)) as archive:
            with io.TextIOWrapper(archive.open("18100245.csv"), encoding="utf-8-sig", newline="") as source:
                snapshot = normalize(csv.DictReader(source))
    root = ROOT / "dist"
    with TemporaryDirectory(dir=ROOT) as temporary:
        staging = Path(temporary) / "dist"
        shutil.copytree(ROOT / "web", staging)
        (staging / "snapshot.json").write_text(json.dumps(snapshot, separators=(",", ":")), encoding="utf-8")
        if root.exists():
            shutil.rmtree(root)
        staging.replace(root)
    print(f"Prepared {len(snapshot['months'])} months for {len(snapshot['products'])} products and {len(snapshot['groups'])} areas.")


if __name__ == "__main__":
    main()
