# Multi-Pharmacy Price Collection System + Patient Savings Engine

A prototype web-scraping pipeline that collects prescription drug prices from
GoodRx and Drugs.com, plus an **intelligent savings engine** that turns those
prices into ranked, actionable savings opportunities for patients.

- **Collection pipeline** — scrapes multiple medications across US locations and
  stores results in `data/price_data.csv`.
- **Savings engine** — compares brand vs. generic, cross-pharmacy price spreads,
  discount cards, manufacturer coupons, and mail-order vs. retail, then scores
  and prioritizes where price-shopping saves the most.

Jump to the reproduced [**Results**](#results): a passing self-test and a full
multi-medication patient action plan (**~$5,625/yr saved, ~93% of spend** for
the example patient).

## Project Structure

```
multi-pharmacy-price-savings/
├── pharmacy_savings/            # the importable package
│   ├── config.py               # medications, locations, scraper settings
│   ├── paths.py                # centralized data/file paths
│   ├── utils.py                # persistence, formatting, logging
│   ├── analysis.py             # descriptive price analysis
│   ├── collection/             # scraping + orchestration
│   │   ├── pipeline.py         # main collection entry point
│   │   ├── scraper_goodrx.py
│   │   ├── scraper_drugs.py
│   │   └── scheduler.py
│   ├── savings/                # the savings engine
│   │   ├── reference.py        # brand/generic map, cards, coupons, weights
│   │   ├── engine.py           # algorithms + multi-med optimizer
│   │   ├── report.py           # CLI reports, patient plans, --selftest
│   │   └── generate_dataset.py # seeded synthetic dataset generator
│   └── examples/
│       └── advanced_example.py
├── data/                       # CSV datasets + example patient profile
│   ├── price_data.csv
│   ├── sample_price_data.csv
│   └── patient_profile_example.json
├── docs/                       # QUICKSTART, SETUP
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

## Quick Start

All commands run from the repository root.

```bash
pip install -r requirements.txt

# Validate the engine (no scraping/network needed)
python -m pharmacy_savings.savings.report --selftest
```

Optionally install the package to get short console commands:

```bash
pip install -e .
```

## Collect Prices

```bash
python -m pharmacy_savings.collection.pipeline     # scrape -> data/price_data.csv
python -m pharmacy_savings.analysis                # descriptive stats
```

## Patient Savings Engine

The engine evaluates five savings levers for every medication and scores each:

| Lever | What it does |
|-------|--------------|
| Pharmacy switch | Finds the cheapest store for the same drug (observed price spread) |
| Generic substitution | Flags brand-name drugs with a cheaper generic equivalent |
| Discount cards | Estimates net price with GoodRx / SingleCare / Cost Plus, etc. |
| Manufacturer coupons | Applies brand copay cards when eligible |
| Mail-order | Compares 90-day maintenance fills vs monthly retail |

### Savings Score

Each opportunity gets a **0-100 Savings Score** blending four factors:

- **Magnitude** (50%) — annualized dollar savings (the money at stake)
- **Recurrence** (20%) — chronic meds save every month; acute courses save once
- **Feasibility** (20%) — how easy the switch is (show a card vs change prescriber)
- **Confidence** (10%) — observed prices score higher than modeled estimates

This ensures patients focus first on medications where price-shopping has the
biggest real-world impact.

### Usage

```bash
# Rank every collected medication by savings potential
python -m pharmacy_savings.savings.report

# Optimize a specific patient's full regimen
python -m pharmacy_savings.savings.report --patient data/patient_profile_example.json

# Use a different data file, or emit JSON
python -m pharmacy_savings.savings.report --data data/sample_price_data.csv --json

# Validate end-to-end against the bundled sample (prints PASS/FAIL)
python -m pharmacy_savings.savings.report --selftest
```

### Larger synthetic dataset

The bundled `data/sample_price_data.csv` is intentionally tiny. To exercise the
engine at scale (and enable price-trend analysis), generate a realistic,
reproducible dataset — ~2,000 records across 32 drug listings, 10 pharmacies,
10 ZIP codes, and 12 weekly snapshots:

```bash
python -m pharmacy_savings.savings.generate_dataset            # -> data/price_data_large.csv
python -m pharmacy_savings.savings.generate_dataset --rows 5000
python -m pharmacy_savings.savings.report --data data/price_data_large.csv --patient data/patient_profile_example.json
```

The generator is deterministic per `--seed`, so anyone regenerates the exact
same data.

### Console commands (after `pip install -e .`)

```bash
pharmacy-collect
pharmacy-analyze
pharmacy-savings --selftest
pharmacy-generate-data --rows 5000
```

## Data Schema

`data/price_data.csv` columns: `timestamp`, `source`, `medication`, `strength`,
`pharmacy`, `price`, `location`, `url`. The savings engine also understands an
optional `drug_type` column (`generic`/`brand`) that improves accuracy but is
not required.

---

## Results

The output below is **actual, reproduced output** from the savings engine
running against the bundled demo dataset (`data/sample_price_data.csv`), not
hand-written. Reproduce it yourself:

```bash
python -m pharmacy_savings.savings.report --selftest
python -m pharmacy_savings.savings.report --data data/sample_price_data.csv --patient data/patient_profile_example.json
```

### 1. Engine self-test (correctness checks)

The `--selftest` flag runs the full engine on the sample data and asserts the
expected behavior of every savings lever and the ranking logic.

```
====================================================================
SAVINGS ENGINE SELF-TEST
====================================================================
[PASS] all sample medications analyzed
[PASS] Lipitor detected as brand
[PASS] Lipitor recommends generic switch (no insurance context)
[PASS] Lipitor is the top-ranked medication
[PASS] acute Amoxicillin scores below all chronic meds
[PASS] Metformin finds a cheaper pharmacy than baseline
[PASS] Lipitor recommends copay card when insured
--------------------------------------------------------------------
7/7 checks passed
```

Each check maps to a requirement:

| Check | Proves |
|-------|--------|
| all sample medications analyzed | Data ingestion + grouping works |
| Lipitor detected as brand | Brand/generic classification |
| Lipitor recommends generic switch (no insurance) | Brand→generic lever |
| Lipitor is the top-ranked medication | Prioritization surfaces biggest impact |
| acute Amoxicillin scores below all chronic meds | Recurrence factor works |
| Metformin finds a cheaper pharmacy | Cross-pharmacy price-spread lever |
| Lipitor recommends copay card when insured | Coupon lever + patient context |

### 2. Multi-medication patient action plan

For patient **Jane Doe** (6 medications, default pharmacy CVS, commercial
insurance), the optimizer ranks prescriptions by **Savings Score** and states
the single best action for each, with alternatives listed underneath.

```
====================================================================
SAVINGS ACTION PLAN FOR: Jane Doe
====================================================================
Estimated current spend: $6,037/yr
Potential savings:       $5,625/yr (~93% of current spend)

Tackle these in order of impact:

1. Lipitor 20mg  -> save $4,692/yr (score 88)
     ACTION: Apply the Lipitor manufacturer copay card
     The maker of Lipitor offers a copay card capping your cost at ~$4.00 per fill (commercial insurance required).
       also: Switch to generic atorvastatin ($4,398/yr)
       also: Move to 90-day mail-order fills ($1,662/yr)

2. Sertraline 50mg  -> save $445/yr (score 58)
     ACTION: Fill at Costco instead
     The same Sertraline 50mg ranges $9.10-$52.75 across pharmacies. Moving to Costco cuts the price ~80%.
       also: Move to 90-day mail-order fills ($473/yr)
       also: Use the Cost Plus Drugs discount card ($428/yr)

3. Levothyroxine 75mcg  -> save $224/yr (score 52)
     ACTION: Fill at Costco instead
     The same Levothyroxine 75mcg ranges $10.25-$32.10 across pharmacies. Moving to Costco cuts the price ~65%.
       also: Use the Cost Plus Drugs discount card ($270/yr)
       also: Move to 90-day mail-order fills ($255/yr)

4. Lisinopril 10mg  -> save $143/yr (score 50)
     ACTION: Fill at Costco instead
     The same Lisinopril 10mg ranges $6.50-$21.00 across pharmacies. Moving to Costco cuts the price ~65%.
       also: Use the Cost Plus Drugs discount card ($170/yr)
       also: Move to 90-day mail-order fills ($162/yr)

5. Metformin 500mg  -> save $108/yr (score 49)
     ACTION: Fill at Costco instead
     The same Metformin 500mg ranges $4.00-$15.75 across pharmacies. Moving to Costco cuts the price ~69%.
       also: Move to 90-day mail-order fills ($120/yr)
       also: Use the Cost Plus Drugs discount card ($118/yr)

6. Amoxicillin 500mg  -> save $14/yr (score 28)
     ACTION: Fill at Walmart instead
     The same Amoxicillin 500mg ranges $6.00-$19.50 across pharmacies. Moving to Walmart cuts the price ~69%.
       also: Use the Cost Plus Drugs discount card ($16/yr)
```

**How to read this:**

| Rank | Medication | Score | Recommended action | Save/yr | Why it ranks here |
|------|-----------|-------|--------------------|---------|-------------------|
| 1 | Lipitor 20mg (brand) | 88 | Manufacturer copay card | $4,692 | Brand drug → huge generic/coupon gap |
| 2 | Sertraline 50mg | 58 | Switch to Costco | $445 | Large cross-pharmacy spread |
| 3 | Levothyroxine 75mcg | 52 | Switch to Costco | $224 | Moderate spread, chronic |
| 4 | Lisinopril 10mg | 50 | Switch to Costco | $143 | Moderate spread, chronic |
| 5 | Metformin 500mg | 49 | Switch to Costco | $108 | Small spread, chronic |
| 6 | Amoxicillin 500mg (acute) | 28 | Switch to Walmart | $14 | Real saving, but fills only once/yr |

**Total: ~$5,625/yr (~93% of current spend)** — driven mostly by the single
brand drug, exactly the kind of high-impact opportunity the scoring is designed
to surface first.

### 3. Scaling up with the synthetic dataset

The two runs above use the tiny bundled sample. For a substantial, realistic
demo, generate a larger dataset and point the same tools at it:

```bash
python -m pharmacy_savings.savings.generate_dataset
# Wrote 2000 records to .../data/price_data_large.csv
#   32 distinct medications, 10 pharmacies, 10 locations, 12 weekly snapshots (seed=42).

python -m pharmacy_savings.savings.report --data data/price_data_large.csv --patient data/patient_profile_example.json
```

This dataset is ~2,000 records across 32 drug listings (16 generics + brands),
10 pharmacies (Costco/Walmart cheap → CVS/Walgreens dear), 10 ZIP codes, and 12
weekly snapshots with a coherent price random-walk so trend analysis works.

### Scoring methodology (why the order looks like this)

The **Savings Score (0–100)** blends four normalized factors:

- **Magnitude (50%)** — annualized dollar savings, saturating at a configurable
  ceiling so a few very large opportunities don't drown out everything else.
- **Recurrence (20%)** — chronic meds save every month; a one-time acute course
  (Amoxicillin) is discounted accordingly.
- **Feasibility (20%)** — how easy the action is (show a discount card vs. get a
  prescriber to approve a substitution).
- **Confidence (10%)** — observed prices (real scraped data) outrank modeled
  estimates (reference multipliers).

> Note: the recommended ACTION is the highest-*score* lever, which can
> occasionally save slightly fewer dollars than an alternative listed beneath it
> (e.g. an easy, high-confidence pharmacy switch chosen over a modeled
> mail-order estimate worth a few dollars more). This is intentional; weights
> live in `pharmacy_savings/savings/reference.py` and are fully tunable.

---

## Limitations & Disclaimer

- GoodRx and Drugs.com use dynamic (JavaScript) content; the simple HTTP
  scraper may not capture all prices. For full reliability use Selenium/Playwright.
- Reference values in `pharmacy_savings/savings/reference.py` (brand multiples,
  coupon copays, card discounts, mail-order assumptions) are **illustrative
  estimates** for demonstration and should be replaced with real, sourced data
  before production use.
- **This project is not medical or financial advice.** Always confirm any
  substitution with a prescriber or pharmacist.

## License

MIT — see [LICENSE](LICENSE).
