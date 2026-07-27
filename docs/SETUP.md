# Setup Guide

## Prerequisites

- Python 3.9+ installed
- pip (Python package manager)

All commands below are run from the repository root.

## Installation

### Step 1: (Recommended) Create a virtual environment

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install dependencies
```bash
pip install -r requirements.txt
```

Or install the package itself (enables the `pharmacy-*` console commands):
```bash
pip install -e .
```

### Step 3: Verify installation
```bash
python -m pharmacy_savings.savings.report --selftest
```

You should see `7/7 checks passed`.

## Project Layout

```
pharmacy_savings/          # the importable package
├── config.py              # medications, locations, scraper settings
├── paths.py               # centralized data/file paths
├── utils.py               # persistence, formatting, logging
├── analysis.py            # descriptive price analysis
├── collection/            # scraping + orchestration
│   ├── pipeline.py        # main collection entry point
│   ├── scraper_goodrx.py
│   ├── scraper_drugs.py
│   └── scheduler.py
├── savings/               # the savings engine
│   ├── reference.py       # brand/generic map, cards, coupons, weights
│   ├── engine.py          # algorithms + multi-med optimizer
│   ├── report.py          # CLI reports, patient plans, --selftest
│   └── generate_dataset.py
└── examples/
    └── advanced_example.py

data/                      # CSV datasets + example patient profile
docs/                      # QUICKSTART, SETUP, RESULTS
```

## Common Tasks

### Collect live prices
```bash
python -m pharmacy_savings.collection.pipeline
```

### Analyze collected data
```bash
python -m pharmacy_savings.analysis
```

### Generate a large synthetic dataset
```bash
python -m pharmacy_savings.savings.generate_dataset --rows 5000
```

### Rank savings / build a patient plan
```bash
python -m pharmacy_savings.savings.report
python -m pharmacy_savings.savings.report --patient data/patient_profile_example.json
```

### Schedule automatic collection
```bash
python -m pharmacy_savings.collection.scheduler
```

## Console commands (after `pip install -e .`)

```bash
pharmacy-collect          # run the collection pipeline
pharmacy-analyze          # descriptive analysis
pharmacy-savings --selftest
pharmacy-generate-data --rows 5000
```

## Troubleshooting

- **`ModuleNotFoundError: pharmacy_savings`** — run commands from the repo root,
  or `pip install -e .`.
- **No prices found when scraping** — GoodRx/Drugs.com need JavaScript; the
  simple HTTP scraper may return nothing. Use the synthetic generator for demos.
- **No data for the report** — generate or collect data first; the report reads
  `data/price_data.csv` by default (override with `--data`).

## Security & Ethics

- Collects public pricing information only; no personal data.
- Respects site Terms of Service with reasonable request behavior.
- Data is stored locally under `data/`.
