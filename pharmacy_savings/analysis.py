"""Simple descriptive analysis of collected price data."""
from .utils import load_existing_data


def analyze_prices(df=None):
    """Print average prices, best deals, and location variation."""
    if df is None:
        df = load_existing_data()

    if df.empty:
        print("No data available. Collect prices first (see README).")
        return

    print("\n" + "=" * 60)
    print("PRICE DATA ANALYSIS")
    print("=" * 60 + "\n")

    print(f"Total Records: {len(df)}")
    print(f"Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Sources: {', '.join(df['source'].unique())}")
    print(f"Medications: {', '.join(df['medication'].unique())}")
    print(f"Locations: {', '.join(df['location'].astype(str).unique())}\n")

    print("Average Price by Medication:")
    print("-" * 60)
    med_prices = df.groupby("medication")["price"].agg(["mean", "min", "max", "count"])
    med_prices.columns = ["Avg Price", "Min Price", "Max Price", "Count"]
    print(med_prices)
    print()

    print("Average Price by Pharmacy:")
    print("-" * 60)
    pharm_prices = df.groupby("pharmacy")["price"].agg(["mean", "min", "max", "count"])
    pharm_prices.columns = ["Avg Price", "Min Price", "Max Price", "Count"]
    print(pharm_prices)
    print()

    print("Average Price by Source:")
    print("-" * 60)
    source_prices = df.groupby("source")["price"].agg(["mean", "min", "max", "count"])
    source_prices.columns = ["Avg Price", "Min Price", "Max Price", "Count"]
    print(source_prices)
    print()

    print("Best Deals (Cheapest Pharmacy for Each Medication):")
    print("-" * 60)
    for med in df["medication"].unique():
        med_df = df[df["medication"] == med].nsmallest(1, "price")
        if not med_df.empty:
            row = med_df.iloc[0]
            print(f"  {med}: ${row['price']:.2f} at {row['pharmacy']} ({row['source']})")
    print()

    print("Price Range by Location:")
    print("-" * 60)
    loc_prices = df.groupby("location")["price"].agg(["mean", "min", "max", "count"])
    loc_prices.columns = ["Avg Price", "Min Price", "Max Price", "Count"]
    print(loc_prices)
    print()


if __name__ == "__main__":
    analyze_prices()
