"""Shared utilities: persistence, formatting, and logging."""
from datetime import datetime
from pathlib import Path

import pandas as pd

from .paths import DEFAULT_PRICE_CSV, ERROR_LOG


def save_price_data(data, filename=None):
    """Append price records to a CSV file (defaults to data/price_data.csv)."""
    if not data:
        return
    path = Path(filename) if filename else DEFAULT_PRICE_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(data)
    df.to_csv(path, index=False, mode="a", header=not path.exists())
    print(f"Saved {len(data)} records to {path}")


def load_existing_data(filename=None):
    """Load a price CSV into a DataFrame (empty DataFrame if it doesn't exist)."""
    path = Path(filename) if filename else DEFAULT_PRICE_CSV
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def format_price(price_str):
    """Extract a numeric price from a string like '$15.99'."""
    try:
        if price_str is None:
            return None
        cleaned = "".join(c for c in str(price_str) if c.isdigit() or c == ".")
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def get_timestamp():
    """Current timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_error(source, medication, location, error_msg):
    """Append an error line to the scraper error log."""
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{get_timestamp()}] {source} | {medication} | {location} | {error_msg}\n")


def normalize_medication_name(name):
    """Normalize a medication name for matching/searching."""
    return name.lower().strip()
