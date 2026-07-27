"""
Synthetic price-data generator.

Produces a large, realistic `price_data.csv`-schema dataset for demos, load
testing, and price-trend analysis. It reuses the savings engine's own
brand/generic knowledge base (`reference.py`) so every generated drug is
something the engine understands.

Prices are modeled as:

    price = base_cash
            * pharmacy_factor        (Costco/Walmart cheap; CVS/Walgreens dear)
            * location_factor         (cost-of-living by ZIP)
            * source_factor           (GoodRx coupon prices < Drugs.com cash)
            * time_factor             (a gentle random walk over the weeks)
            * noise                   (small per-observation jitter)

Brand rows use the generic base price multiplied by the brand cash multiple
from `reference.BRAND_GENERIC_MAP`.

Everything is deterministic for a given --seed, so results are reproducible.

Run with:  python -m pharmacy_savings.savings.generate_dataset [options]
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta

from ..paths import LARGE_PRICE_CSV
from . import reference as cfg

# --- Realistic 30-day generic cash prices (USD) ----------------------------
GENERIC_BASE_PRICE = {
    "metformin": 9.0,   "lisinopril": 12.0,  "atorvastatin": 15.0, "amoxicillin": 12.0,
    "sertraline": 18.0, "escitalopram": 20.0, "omeprazole": 14.0,  "pantoprazole": 16.0,
    "rosuvastatin": 22.0, "simvastatin": 12.0, "losartan": 13.0,   "amlodipine": 11.0,
    "levothyroxine": 15.0, "gabapentin": 17.0, "montelukast": 19.0, "duloxetine": 24.0,
}

# One representative strength per drug.
DRUG_STRENGTH = {
    "metformin": "500mg", "lisinopril": "10mg", "atorvastatin": "20mg", "amoxicillin": "500mg",
    "sertraline": "50mg", "escitalopram": "10mg", "omeprazole": "20mg", "pantoprazole": "40mg",
    "rosuvastatin": "10mg", "simvastatin": "20mg", "losartan": "50mg", "amlodipine": "5mg",
    "levothyroxine": "75mcg", "gabapentin": "300mg", "montelukast": "10mg", "duloxetine": "30mg",
}

# --- Pharmacies and their relative price level -----------------------------
PHARMACY_FACTOR = {
    "CVS": 1.60, "Walgreens": 1.50, "Rite Aid": 1.45, "Kroger": 1.20, "Publix": 1.15,
    "H-E-B": 1.10, "Amazon Pharmacy": 0.90, "Walmart": 0.85, "Sam's Club": 0.80, "Costco": 0.70,
}

# --- Locations (ZIP -> cost-of-living factor) ------------------------------
LOCATION_FACTOR = {
    "90210": 1.25, "10001": 1.20, "02108": 1.18, "98101": 1.12, "19103": 1.03,
    "60601": 1.05, "30301": 1.00, "33101": 1.00, "85001": 0.95, "77001": 0.92,
}

SOURCE_FACTOR = {"GoodRx": 0.80, "Drugs.com": 1.00}
SOURCE_URL = {"GoodRx": "https://goodrx.com", "Drugs.com": "https://drugs.com"}

FIELDS = ["timestamp", "source", "medication", "strength", "pharmacy",
          "price", "location", "url", "drug_type"]


def _weekly_dates(weeks: int, end: datetime) -> list[datetime]:
    """Return `weeks` weekly snapshot datetimes ending at `end`."""
    return [end - timedelta(weeks=(weeks - 1 - i)) for i in range(weeks)]


def build_listings() -> list[tuple[str, str, float, str]]:
    """
    Expand the knowledge base into (medication, strength, base_price, drug_type)
    listings: every generic plus, where one exists, its brand.
    """
    listings: list[tuple[str, str, float, str]] = []
    for generic, base in GENERIC_BASE_PRICE.items():
        strength = DRUG_STRENGTH.get(generic, "")
        listings.append((generic.capitalize(), strength, base, "generic"))
        bg = cfg.BRAND_GENERIC_MAP.get(generic)
        if bg:
            brand_base = base * bg["brand_cash_multiple"]
            listings.append((bg["brand"], strength, brand_base, "brand"))
    return listings


def generate(rows: int, seed: int, weeks: int) -> list[dict]:
    rng = random.Random(seed)
    listings = build_listings()
    pharmacies = list(PHARMACY_FACTOR)
    locations = list(LOCATION_FACTOR)
    sources = list(SOURCE_FACTOR)
    dates = _weekly_dates(weeks, datetime(2026, 7, 20, 9, 0, 0))

    # A gentle per-listing price trend (random walk) shared across the weeks so
    # that time-series analysis shows coherent movement, not pure noise.
    trend = {}
    for med, strength, _base, dtype in listings:
        walk, level = [], 1.0
        for _ in dates:
            level *= 1.0 + rng.uniform(-0.02, 0.02)
            walk.append(level)
        trend[(med, strength, dtype)] = walk

    # Enumerate all possible observations, then sample `rows` of them.
    combos = [
        (li, ph, loc, src, di)
        for li in range(len(listings))
        for ph in pharmacies
        for loc in locations
        for src in sources
        for di in range(len(dates))
    ]
    rng.shuffle(combos)
    combos = combos[:min(rows, len(combos))]

    records = []
    for li, pharmacy, location, source, di in combos:
        med, strength, base, dtype = listings[li]
        factor = (PHARMACY_FACTOR[pharmacy] * LOCATION_FACTOR[location]
                  * SOURCE_FACTOR[source] * trend[(med, strength, dtype)][di]
                  * rng.uniform(0.94, 1.06))
        price = round(base * factor, 2)
        records.append({
            "timestamp": dates[di].strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "medication": med,
            "strength": strength,
            "pharmacy": pharmacy,
            "price": price,
            "location": location,
            "url": SOURCE_URL[source],
            "drug_type": dtype,
        })

    records.sort(key=lambda r: (r["timestamp"], r["medication"], r["pharmacy"]))
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a synthetic pharmacy price dataset.")
    parser.add_argument("--rows", type=int, default=2000, help="Number of price records (default 2000).")
    parser.add_argument("--weeks", type=int, default=12, help="Weekly snapshots for trend data (default 12).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default 42).")
    parser.add_argument("--out", default=str(LARGE_PRICE_CSV), help="Output CSV path.")
    args = parser.parse_args(argv)

    records = generate(args.rows, args.seed, args.weeks)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    meds = sorted({r["medication"] for r in records})
    print(f"Wrote {len(records)} records to {args.out}")
    print(f"  {len(meds)} distinct medications, "
          f"{len(PHARMACY_FACTOR)} pharmacies, {len(LOCATION_FACTOR)} locations, "
          f"{args.weeks} weekly snapshots (seed={args.seed}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
