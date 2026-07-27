"""
Reference data and tunable parameters for the patient-savings engine.

This module is the single place to curate the domain knowledge the savings
algorithms rely on. Everything here is an editable, illustrative estimate --
NOT medical or financial advice. Numbers are intentionally conservative and
should be replaced with real, sourced data (e.g. live coupon APIs, PBM feeds,
manufacturer copay-card terms) before production use.

All price estimates are expressed for a standard 30-day fill unless noted.
"""

# ---------------------------------------------------------------------------
# 1. Brand <-> generic knowledge base
# ---------------------------------------------------------------------------
# For each generic (the name the scraper collects), we record the brand it can
# replace and how much more the brand typically costs as a CASH multiple of the
# generic cash price. Multipliers are rough national averages; a value of 10.0
# means the brand runs ~10x the generic.
#
# `generic_available = True` means a therapeutically-equivalent generic exists,
# so brand->generic substitution is a viable lever for the patient.

BRAND_GENERIC_MAP = {
    "metformin":     {"brand": "Glucophage", "brand_cash_multiple": 8.0,  "generic_available": True},
    "lisinopril":    {"brand": "Prinivil",   "brand_cash_multiple": 9.0,  "generic_available": True},
    "atorvastatin":  {"brand": "Lipitor",    "brand_cash_multiple": 12.0, "generic_available": True},
    "amoxicillin":   {"brand": "Amoxil",     "brand_cash_multiple": 4.0,  "generic_available": True},
    "sertraline":    {"brand": "Zoloft",     "brand_cash_multiple": 11.0, "generic_available": True},
    "escitalopram":  {"brand": "Lexapro",    "brand_cash_multiple": 13.0, "generic_available": True},
    "omeprazole":    {"brand": "Prilosec",   "brand_cash_multiple": 6.0,  "generic_available": True},
    "pantoprazole":  {"brand": "Protonix",   "brand_cash_multiple": 7.0,  "generic_available": True},
    "rosuvastatin":  {"brand": "Crestor",    "brand_cash_multiple": 14.0, "generic_available": True},
    "simvastatin":   {"brand": "Zocor",      "brand_cash_multiple": 10.0, "generic_available": True},
    "losartan":      {"brand": "Cozaar",     "brand_cash_multiple": 9.0,  "generic_available": True},
    "amlodipine":    {"brand": "Norvasc",    "brand_cash_multiple": 9.0,  "generic_available": True},
    "levothyroxine": {"brand": "Synthroid",  "brand_cash_multiple": 5.0,  "generic_available": True},
    "gabapentin":    {"brand": "Neurontin",  "brand_cash_multiple": 8.0,  "generic_available": True},
    "montelukast":   {"brand": "Singulair",  "brand_cash_multiple": 12.0, "generic_available": True},
    "duloxetine":    {"brand": "Cymbalta",   "brand_cash_multiple": 13.0, "generic_available": True},
}

# Reverse lookup: brand name (lowercased) -> generic name.
BRAND_TO_GENERIC = {
    info["brand"].lower(): generic for generic, info in BRAND_GENERIC_MAP.items()
}


# ---------------------------------------------------------------------------
# 2. Clinical / usage metadata (drives recurrence + annualization)
# ---------------------------------------------------------------------------
# `chronic` meds are taken indefinitely, so savings recur every fill -> high
# impact. `fills_per_year` is the default retail cadence (monthly = 12).
# Acute courses (e.g. an antibiotic) are typically filled ~1x/year.

DRUG_USAGE = {
    "metformin":     {"chronic": True,  "fills_per_year": 12, "category": "Diabetes"},
    "lisinopril":    {"chronic": True,  "fills_per_year": 12, "category": "Blood pressure"},
    "atorvastatin":  {"chronic": True,  "fills_per_year": 12, "category": "Cholesterol"},
    "rosuvastatin":  {"chronic": True,  "fills_per_year": 12, "category": "Cholesterol"},
    "simvastatin":   {"chronic": True,  "fills_per_year": 12, "category": "Cholesterol"},
    "losartan":      {"chronic": True,  "fills_per_year": 12, "category": "Blood pressure"},
    "amlodipine":    {"chronic": True,  "fills_per_year": 12, "category": "Blood pressure"},
    "levothyroxine": {"chronic": True,  "fills_per_year": 12, "category": "Thyroid"},
    "sertraline":    {"chronic": True,  "fills_per_year": 12, "category": "Mental health"},
    "escitalopram":  {"chronic": True,  "fills_per_year": 12, "category": "Mental health"},
    "duloxetine":    {"chronic": True,  "fills_per_year": 12, "category": "Mental health"},
    "omeprazole":    {"chronic": True,  "fills_per_year": 12, "category": "Acid reflux"},
    "pantoprazole":  {"chronic": True,  "fills_per_year": 12, "category": "Acid reflux"},
    "gabapentin":    {"chronic": True,  "fills_per_year": 12, "category": "Nerve pain"},
    "montelukast":   {"chronic": True,  "fills_per_year": 12, "category": "Asthma/allergy"},
    "amoxicillin":   {"chronic": False, "fills_per_year": 1,  "category": "Antibiotic"},
}

# Fallback when a drug is unknown to the tables above.
DEFAULT_USAGE = {"chronic": True, "fills_per_year": 12, "category": "Unknown"}


# ---------------------------------------------------------------------------
# 3. Discount card programs
# ---------------------------------------------------------------------------
# Each card yields an estimated NET price = reference_cash_price * (1 - discount)
# for the drug type it applies to. `applies_to` filters generic vs brand.
# `effort` (0-1, lower = easier) feeds the feasibility part of the score.
# These programs are free to the patient and require no insurance.

DISCOUNT_CARDS = [
    {"name": "GoodRx",          "generic_discount": 0.70, "brand_discount": 0.30, "applies_to": "both",    "effort": 0.10},
    {"name": "SingleCare",      "generic_discount": 0.72, "brand_discount": 0.28, "applies_to": "both",    "effort": 0.10},
    {"name": "RxSaver",         "generic_discount": 0.65, "brand_discount": 0.25, "applies_to": "both",    "effort": 0.15},
    {"name": "Cost Plus Drugs", "generic_discount": 0.80, "brand_discount": 0.00, "applies_to": "generic", "effort": 0.25},
    {"name": "Amazon Pharmacy", "generic_discount": 0.75, "brand_discount": 0.20, "applies_to": "both",    "effort": 0.20},
]


# ---------------------------------------------------------------------------
# 4. Manufacturer coupons / copay cards (brand-name drugs only)
# ---------------------------------------------------------------------------
# Copay cards cap the patient's out-of-pocket on a BRAND to a fixed dollar
# amount, but usually require commercial (non-government) insurance. Keyed by
# brand name (lowercased).

MANUFACTURER_COUPONS = {
    "lipitor":   {"copay": 4.0,  "requires_commercial_insurance": True},
    "crestor":   {"copay": 3.0,  "requires_commercial_insurance": True},
    "zoloft":    {"copay": 10.0, "requires_commercial_insurance": True},
    "lexapro":   {"copay": 10.0, "requires_commercial_insurance": True},
    "cymbalta":  {"copay": 25.0, "requires_commercial_insurance": True},
    "singulair": {"copay": 15.0, "requires_commercial_insurance": True},
    "synthroid": {"copay": 25.0, "requires_commercial_insurance": True},
}


# ---------------------------------------------------------------------------
# 5. Mail-order vs. retail
# ---------------------------------------------------------------------------
# Mail-order fills a 90-day supply. Instead of paying 3x a 30-day retail price,
# a 90-day mail-order fill typically costs `bulk_90day_multiple` x the 30-day
# price, and per-unit pricing is often discounted (`per_unit_discount`).
# Shipping is generally free. Only worthwhile for chronic (maintenance) meds.

MAIL_ORDER = {
    "bulk_90day_multiple": 2.5,   # pay ~2.5 x a 30-day price for 90 days
    "per_unit_discount": 0.10,    # additional markdown vs retail cash
    "only_for_chronic": True,
    "effort": 0.30,               # setup with a mail-order pharmacy
}


# ---------------------------------------------------------------------------
# 6. Savings-score weights and effort model
# ---------------------------------------------------------------------------
# The composite Savings Score (0-100) blends four normalized factors:
#   - magnitude:   annualized dollar savings (the money at stake)
#   - recurrence:  how often the saving repeats (chronic vs acute)
#   - feasibility: how easy the switch is (1 - effort)
#   - confidence:  how trustworthy the estimate is (observed data > modeled)
SCORE_WEIGHTS = {
    "magnitude": 0.50,
    "recurrence": 0.20,
    "feasibility": 0.20,
    "confidence": 0.10,
}

# Effort (0-1, lower = easier) by lever type; drives the feasibility factor.
LEVER_EFFORT = {
    "pharmacy_switch": 0.15,   # just fill at a different store
    "generic_switch": 0.40,    # needs prescriber / pharmacist sign-off
    "discount_card": 0.10,     # show a card at the counter
    "manufacturer_coupon": 0.35,
    "mail_order": 0.30,
}

# Confidence (0-1) by evidence type; drives the confidence factor.
LEVER_CONFIDENCE = {
    "observed": 0.95,   # computed from real scraped prices
    "modeled": 0.55,    # estimated from reference multipliers
}

# Annual-savings value (in dollars) that maps to a full magnitude score of 1.0.
# Savings at/above this are treated as "maximum impact"; tune to your population.
MAGNITUDE_SATURATION_USD = 2000.0

# Ignore opportunities below this annual dollar amount as noise.
MIN_ANNUAL_SAVINGS_USD = 5.0
