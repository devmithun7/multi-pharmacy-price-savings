"""
Advanced usage examples - customize the system for your needs.

Run with:  python -m pharmacy_savings.examples.advanced_example
(Uncomment the examples you want at the bottom of the file.)
"""
import pandas as pd

from ..paths import DEFAULT_PRICE_CSV
from ..utils import save_price_data
from ..collection.scraper_goodrx import GoodRxScraper

DATA = str(DEFAULT_PRICE_CSV)


def example_single_medication():
    """Collect prices for just one medication."""
    print("Example 1: Single Medication Collection")
    print("-" * 60)
    scraper = GoodRxScraper()
    results = scraper.search_medication("Metformin", "500mg", "90210")
    for result in results:
        print(f"  {result['pharmacy']}: ${result['price']}")
    save_price_data(results)


def example_custom_medications():
    """Use a custom list of medications."""
    print("\nExample 2: Custom Medications")
    print("-" * 60)
    custom_meds = [
        {"name": "Aspirin", "strength": "325mg", "quantity": 100},
        {"name": "Ibuprofen", "strength": "200mg", "quantity": 50},
    ]
    custom_locations = [{"zipcode": "10001", "city": "New York"}]
    goodrx = GoodRxScraper()
    results = goodrx.scrape_all(custom_meds, custom_locations)
    print(f"Collected {len(results)} records")
    save_price_data(results)


def example_find_cheapest():
    """Find the absolute cheapest option across all sources."""
    print("\nExample 3: Find Cheapest Option")
    print("-" * 60)
    df = pd.read_csv(DATA)
    cheapest = df.loc[df["price"].idxmin()]
    print("Overall Cheapest:")
    print(f"  {cheapest['medication']} ({cheapest['strength']})")
    print(f"  ${cheapest['price']:.2f} at {cheapest['pharmacy']}")
    print(f"  Source: {cheapest['source']}")
    print(f"  Location: {cheapest['location']}")


def example_price_comparison():
    """Compare prices for one medication across pharmacies."""
    print("\nExample 4: Price Comparison")
    print("-" * 60)
    df = pd.read_csv(DATA)
    med_df = df[df["medication"] == "Metformin"].sort_values("price")
    print("Metformin Prices (sorted by cost):")
    for _, row in med_df.iterrows():
        print(f"  ${row['price']:6.2f} - {row['pharmacy']:20s} ({row['source']})")


def example_best_deals_by_location():
    """Find the best deal for each location."""
    print("\nExample 5: Best Deals by Location")
    print("-" * 60)
    df = pd.read_csv(DATA)
    for location in df["location"].unique():
        loc_df = df[df["location"] == location]
        cheapest = loc_df.loc[loc_df["price"].idxmin()]
        print(f"{location}: ${cheapest['price']:.2f} ({cheapest['pharmacy']})")


def example_price_trends():
    """Track price changes over time (needs multiple snapshots)."""
    print("\nExample 6: Price Trends")
    print("-" * 60)
    df = pd.read_csv(DATA)
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    trend = df.groupby(["medication", "date"])["price"].mean()
    print("Average prices by date:")
    for med in df["medication"].unique():
        print(f"\n{med}:")
        for date, price in trend[med].items():
            print(f"  {date}: ${price:.2f}")


def example_export_formats():
    """Export data in different formats."""
    print("\nExample 7: Export Formats")
    print("-" * 60)
    df = pd.read_csv(DATA)
    df.to_json("price_data.json", orient="records", indent=2)
    print("Exported to JSON: price_data.json")
    df.to_excel("price_data.xlsx", index=False)
    print("Exported to Excel: price_data.xlsx")
    with open("price_report.html", "w", encoding="utf-8") as f:
        f.write(df.to_html())
    print("Exported to HTML: price_report.html")


if __name__ == "__main__":
    print("=" * 60)
    print("ADVANCED USAGE EXAMPLES")
    print("=" * 60)

    # Uncomment the examples you want to run:
    # example_single_medication()
    # example_custom_medications()
    # example_find_cheapest()
    # example_price_comparison()
    # example_best_deals_by_location()
    # example_price_trends()
    # example_export_formats()

    print("\nNote: Uncomment examples in this file to run them.")
    print("Make sure you have collected/generated price data first.")
