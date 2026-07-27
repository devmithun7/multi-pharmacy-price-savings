# Quick Start (30 seconds)

All commands are run from the repository root.

## 1. Install Python packages
```bash
pip install -r requirements.txt
```

## 2. See the savings engine in action (no scraping needed)

Validate everything works:
```bash
python -m pharmacy_savings.savings.report --selftest
```

Generate a realistic dataset and get a patient action plan:
```bash
python -m pharmacy_savings.savings.generate_dataset
python -m pharmacy_savings.savings.report --data data/price_data_large.csv --patient data/patient_profile_example.json
```

## 3. (Optional) Collect live prices
```bash
python -m pharmacy_savings.collection.pipeline
python -m pharmacy_savings.analysis
```

Saves to `data/price_data.csv`.

---

## Next Steps

- **Edit medications/locations**: `pharmacy_savings/config.py`
- **Tune savings assumptions**: `pharmacy_savings/savings/reference.py`
- **Schedule runs**: `python -m pharmacy_savings.collection.scheduler`
- **See results**: [Results section in the README](../README.md#results)

See [SETUP.md](SETUP.md) for more detail.
