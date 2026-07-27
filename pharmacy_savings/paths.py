"""
Central filesystem paths for the project.

Everything resolves relative to the package location, so the tools work no
matter what directory you launch them from.
"""
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent          # .../pharmacy_savings
ROOT_DIR = PACKAGE_DIR.parent                          # repo root
DATA_DIR = ROOT_DIR / "data"

# Canonical data files.
DEFAULT_PRICE_CSV = DATA_DIR / "price_data.csv"
SAMPLE_PRICE_CSV = DATA_DIR / "sample_price_data.csv"
LARGE_PRICE_CSV = DATA_DIR / "price_data_large.csv"
EXAMPLE_PATIENT = DATA_DIR / "patient_profile_example.json"

# Log file (git-ignored).
ERROR_LOG = ROOT_DIR / "scraper_errors.log"
