"""
Main price-collection pipeline.

Run with:  python -m pharmacy_savings.collection.pipeline
"""
import time

from ..config import MEDICATIONS, LOCATIONS
from ..utils import save_price_data, get_timestamp
from .scraper_goodrx import GoodRxScraper
from .scraper_drugs import DrugsScraper


def run_collection():
    """Run the full price collection pipeline."""
    print("=" * 60)
    print("Starting Pharmacy Price Collection Pipeline")
    print(f"Time: {get_timestamp()}")
    print("=" * 60)
    print()

    all_data = []
    goodrx = GoodRxScraper()
    drugs = DrugsScraper()

    print("[1/2] Running GoodRx Scraper...")
    print("-" * 60)
    try:
        goodrx_data = goodrx.scrape_all(MEDICATIONS, LOCATIONS)
        all_data.extend(goodrx_data)
        print(f"Collected {len(goodrx_data)} records from GoodRx\n")
    except Exception as e:
        print(f"GoodRx scraper failed: {e}\n")

    time.sleep(2)  # be respectful between sources

    print("[2/2] Running Drugs.com Scraper...")
    print("-" * 60)
    try:
        drugs_data = drugs.scrape_all(MEDICATIONS, LOCATIONS)
        all_data.extend(drugs_data)
        print(f"Collected {len(drugs_data)} records from Drugs.com\n")
    except Exception as e:
        print(f"Drugs.com scraper failed: {e}\n")

    print("=" * 60)
    print("Saving Results...")
    print("=" * 60)
    if all_data:
        save_price_data(all_data)
        print(f"\nTotal records collected: {len(all_data)}")
    else:
        print("\nNo data collected. Check logs for details.")

    print(f"\nCompleted at: {get_timestamp()}")
    print("=" * 60)


if __name__ == "__main__":
    run_collection()
