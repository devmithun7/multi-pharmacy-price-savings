"""
Patient-savings engine.

Consumes the price data produced by the collection pipeline (``price_data.csv``
with columns: timestamp, source, medication, strength, pharmacy, price,
location, url) and turns raw prices into *ranked, actionable savings
opportunities* for a patient.

Five savings levers are evaluated for every medication:
  1. Pharmacy switch     -- same drug, cheaper store (observed price spread)
  2. Generic substitution -- brand -> therapeutically-equivalent generic
  3. Discount cards      -- GoodRx / SingleCare / Cost Plus, etc.
  4. Manufacturer coupons -- brand copay cards
  5. Mail-order          -- 90-day maintenance fills vs monthly retail

Each opportunity gets a 0-100 **Savings Score** that blends how much money is
at stake (annualized), how often it recurs, how easy the switch is, and how
confident we are in the estimate. A multi-medication optimizer then tells a
patient which of their prescriptions to tackle first.

Nothing here is medical or financial advice; always confirm substitutions with
a prescriber or pharmacist.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field, asdict
from typing import Optional

import pandas as pd

from ..utils import load_existing_data, normalize_medication_name
from . import reference as cfg


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class SavingsOpportunity:
    """A single actionable way to save on one medication."""
    lever: str                     # e.g. "pharmacy_switch"
    title: str                     # human-readable headline
    detail: str                    # explanation of the recommended action
    baseline_price: float          # current per-fill (30-day) cost
    optimized_price: float         # per-fill cost after taking the action
    per_fill_savings: float
    annual_savings: float
    feasibility: float             # 0-1 (1 = effortless)
    confidence: float              # 0-1 (1 = certain)
    score: float = 0.0             # 0-100 composite Savings Score

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class MedicationSavings:
    """All savings opportunities discovered for one medication+strength."""
    medication: str
    strength: str
    drug_type: str                 # "generic" | "brand" | "unknown"
    category: str
    chronic: bool
    fills_per_year: int
    baseline_price: float
    best_observed_price: float
    best_observed_pharmacy: str
    price_spread: float            # max - min across observed pharmacies
    opportunities: list[SavingsOpportunity] = field(default_factory=list)

    @property
    def top_opportunity(self) -> Optional[SavingsOpportunity]:
        """The single recommended action = highest Savings Score."""
        return max(self.opportunities, key=lambda o: o.score) if self.opportunities else None

    @property
    def recommended_annual_savings(self) -> float:
        """Annual savings of the recommended (highest-score) action."""
        top = self.top_opportunity
        return top.annual_savings if top else 0.0

    @property
    def max_annual_savings(self) -> float:
        """Largest annual savings across all levers (aspirational ceiling)."""
        return max((o.annual_savings for o in self.opportunities), default=0.0)

    @property
    def savings_score(self) -> float:
        """Headline score for the medication = its recommended action."""
        top = self.top_opportunity
        return top.score if top else 0.0


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------
def classify_drug_type(name: str, explicit: Optional[str] = None) -> str:
    """Decide whether a row is a brand or generic drug."""
    if explicit and str(explicit).strip().lower() in ("brand", "generic"):
        return str(explicit).strip().lower()
    key = normalize_medication_name(name)
    if key in cfg.BRAND_TO_GENERIC:
        return "brand"
    if key in cfg.BRAND_GENERIC_MAP:
        return "generic"
    return "generic"  # scraped configs collect generic names by default


def generic_name_for(name: str) -> str:
    """Return the generic name for a brand, or the name itself if already generic."""
    key = normalize_medication_name(name)
    return cfg.BRAND_TO_GENERIC.get(key, key)


def usage_for(generic_key: str) -> dict:
    return cfg.DRUG_USAGE.get(generic_key, cfg.DEFAULT_USAGE)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def _magnitude_factor(annual_savings: float) -> float:
    return min(annual_savings / cfg.MAGNITUDE_SATURATION_USD, 1.0)


def _recurrence_factor(fills_per_year: int) -> float:
    # 12 fills/yr (monthly, chronic) -> 1.0; a single acute fill -> ~0.08.
    return min(fills_per_year / 12.0, 1.0)


def compute_score(annual_savings: float, fills_per_year: int,
                  feasibility: float, confidence: float) -> float:
    """Blend the four normalized factors into a 0-100 Savings Score."""
    w = cfg.SCORE_WEIGHTS
    raw = (
        w["magnitude"] * _magnitude_factor(annual_savings)
        + w["recurrence"] * _recurrence_factor(fills_per_year)
        + w["feasibility"] * feasibility
        + w["confidence"] * confidence
    )
    return round(100.0 * raw, 1)


def _make_opportunity(lever: str, title: str, detail: str, baseline: float,
                      optimized: float, fills_per_year: int,
                      confidence_kind: str) -> Optional[SavingsOpportunity]:
    """Build an opportunity, returning None if the saving is negligible."""
    per_fill = round(baseline - optimized, 2)
    annual = round(per_fill * fills_per_year, 2)
    if annual < cfg.MIN_ANNUAL_SAVINGS_USD:
        return None
    feasibility = 1.0 - cfg.LEVER_EFFORT.get(lever, 0.3)
    confidence = cfg.LEVER_CONFIDENCE[confidence_kind]
    opp = SavingsOpportunity(
        lever=lever,
        title=title,
        detail=detail,
        baseline_price=round(baseline, 2),
        optimized_price=round(optimized, 2),
        per_fill_savings=per_fill,
        annual_savings=annual,
        feasibility=round(feasibility, 2),
        confidence=confidence,
    )
    opp.score = compute_score(annual, fills_per_year, feasibility, confidence)
    return opp


# ---------------------------------------------------------------------------
# Core: analyze one medication
# ---------------------------------------------------------------------------
def analyze_medication(rows: pd.DataFrame, *,
                       current_pharmacy: Optional[str] = None,
                       on_brand: bool = False,
                       has_commercial_insurance: bool = False
                       ) -> Optional[MedicationSavings]:
    """
    Evaluate every savings lever for a single medication+strength group.

    ``rows`` is the subset of the price table for one (medication, strength).
    """
    if rows.empty:
        return None

    name = str(rows.iloc[0]["medication"])
    strength = str(rows.iloc[0].get("strength", ""))
    explicit_type = rows.iloc[0].get("drug_type") if "drug_type" in rows.columns else None

    prices = [float(p) for p in rows["price"].dropna().tolist() if float(p) > 0]
    if not prices:
        return None

    generic_key = generic_name_for(name)
    usage = usage_for(generic_key)
    fills = usage["fills_per_year"]
    chronic = usage["chronic"]

    drug_type = "brand" if on_brand else classify_drug_type(name, explicit_type)

    best_price = min(prices)
    worst_price = max(prices)
    median_price = statistics.median(prices)
    best_row = rows.loc[rows["price"].astype(float).idxmin()]
    best_pharmacy = str(best_row["pharmacy"])

    # Baseline = what the patient pays today. Use their current pharmacy's price
    # when known, otherwise the median observed price (a "typical, unshopped"
    # cost). Retail cash reference (for card math) = the highest observed price.
    baseline = median_price
    if current_pharmacy:
        match = rows[rows["pharmacy"].str.lower() == current_pharmacy.lower()]
        if not match.empty:
            baseline = float(match["price"].astype(float).min())
    retail_cash = worst_price

    med = MedicationSavings(
        medication=name,
        strength=strength,
        drug_type=drug_type,
        category=usage["category"],
        chronic=chronic,
        fills_per_year=fills,
        baseline_price=round(baseline, 2),
        best_observed_price=round(best_price, 2),
        best_observed_pharmacy=best_pharmacy,
        price_spread=round(worst_price - best_price, 2),
    )

    # --- Lever 1: pharmacy switch (observed price spread) ------------------
    if best_price < baseline:
        pct = (baseline - best_price) / baseline * 100 if baseline else 0
        opp = _make_opportunity(
            "pharmacy_switch",
            f"Fill at {best_pharmacy} instead",
            f"The same {name} {strength} ranges ${best_price:.2f}-${worst_price:.2f} "
            f"across pharmacies. Moving to {best_pharmacy} cuts the price ~{pct:.0f}%.",
            baseline, best_price, fills, "observed",
        )
        if opp:
            med.opportunities.append(opp)

    # --- Lever 2: brand -> generic substitution ----------------------------
    bg = cfg.BRAND_GENERIC_MAP.get(generic_key)
    if drug_type == "brand" and bg and bg["generic_available"]:
        # Model the generic's price from the brand's cheapest observed price
        # and the known brand/generic cash multiple.
        generic_price = best_price / bg["brand_cash_multiple"]
        opp = _make_opportunity(
            "generic_switch",
            f"Switch to generic {generic_key}",
            f"{name} is the brand for {generic_key}. The generic is "
            f"therapeutically equivalent and runs ~{bg['brand_cash_multiple']:.0f}x "
            f"cheaper. Ask your prescriber to allow generic substitution.",
            baseline, generic_price, fills, "modeled",
        )
        if opp:
            med.opportunities.append(opp)

    # --- Lever 3: discount cards -------------------------------------------
    best_card = None
    for card in cfg.DISCOUNT_CARDS:
        if card["applies_to"] == "generic" and drug_type != "generic":
            continue
        if card["applies_to"] == "brand" and drug_type != "brand":
            continue
        discount = card["generic_discount"] if drug_type == "generic" else card["brand_discount"]
        if discount <= 0:
            continue
        net = retail_cash * (1 - discount)
        if best_card is None or net < best_card[1]:
            best_card = (card["name"], net, discount)
    if best_card:
        card_name, card_net, discount = best_card
        opp = _make_opportunity(
            "discount_card",
            f"Use the {card_name} discount card",
            f"A free {card_name} coupon takes the cash price down ~{discount*100:.0f}% "
            f"to about ${card_net:.2f}. No insurance required -- show it at the counter.",
            baseline, card_net, fills, "modeled",
        )
        if opp:
            med.opportunities.append(opp)

    # --- Lever 4: manufacturer coupon (brand copay card) -------------------
    if drug_type == "brand":
        brand_key = normalize_medication_name(name)
        coupon = cfg.MANUFACTURER_COUPONS.get(brand_key)
        if coupon and (has_commercial_insurance or not coupon["requires_commercial_insurance"]):
            opp = _make_opportunity(
                "manufacturer_coupon",
                f"Apply the {name} manufacturer copay card",
                f"The maker of {name} offers a copay card capping your cost at "
                f"~${coupon['copay']:.2f} per fill"
                + (" (commercial insurance required)." if coupon["requires_commercial_insurance"] else "."),
                baseline, coupon["copay"], fills, "modeled",
            )
            if opp:
                med.opportunities.append(opp)

    # --- Lever 5: mail-order (90-day maintenance fills) --------------------
    mail_order_applicable = chronic or not cfg.MAIL_ORDER["only_for_chronic"]
    if mail_order_applicable:
        # Buy the cheapest available drug in 90-day quantities: a 90-day fill
        # costs ~bulk_90day_multiple x a 30-day price (vs 3x monthly) plus a
        # per-unit discount. Expressed per-30-day-equivalent for comparability.
        per_30_equiv = best_price * (cfg.MAIL_ORDER["bulk_90day_multiple"] / 3.0) \
                       * (1 - cfg.MAIL_ORDER["per_unit_discount"])
        opp = _make_opportunity(
            "mail_order",
            "Move to 90-day mail-order fills",
            f"For a maintenance med, a 90-day mail-order supply costs about "
            f"{cfg.MAIL_ORDER['bulk_90day_multiple']:.1f}x a 30-day fill (vs 3x) with "
            f"free shipping -- roughly ${per_30_equiv:.2f} per 30-day-equivalent.",
            baseline, per_30_equiv, fills, "modeled",
        )
        if opp:
            med.opportunities.append(opp)

    return med if med.opportunities or med.price_spread > 0 else med


# ---------------------------------------------------------------------------
# Core: analyze an entire price table
# ---------------------------------------------------------------------------
def analyze_all(df: Optional[pd.DataFrame] = None) -> list[MedicationSavings]:
    """Analyze every medication+strength in the price table (or the CSV)."""
    if df is None:
        df = load_existing_data()
    if df is None or df.empty:
        return []

    df = df.copy()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])

    results: list[MedicationSavings] = []
    group_cols = ["medication", "strength"] if "strength" in df.columns else ["medication"]
    for _, group in df.groupby(group_cols, dropna=False):
        med = analyze_medication(group)
        if med:
            results.append(med)

    results.sort(key=lambda m: m.savings_score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Multi-medication patient optimizer
# ---------------------------------------------------------------------------
@dataclass
class PatientMedication:
    name: str
    strength: str = ""
    current_pharmacy: Optional[str] = None
    on_brand: bool = False
    has_commercial_insurance: bool = False


@dataclass
class PatientPlan:
    medications: list[MedicationSavings]
    total_annual_savings: float
    total_current_annual_cost: float

    @property
    def prioritized(self) -> list[MedicationSavings]:
        """Medications ranked by Savings Score (biggest impact first)."""
        return sorted(self.medications, key=lambda m: m.savings_score, reverse=True)


def optimize_patient(patient_meds: list[PatientMedication],
                     df: Optional[pd.DataFrame] = None) -> PatientPlan:
    """
    Given the full medication list for one patient, find and rank the biggest
    savings opportunities across their regimen.
    """
    if df is None:
        df = load_existing_data()
    if df is None or df.empty:
        return PatientPlan([], 0.0, 0.0)

    df = df.copy()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])

    results: list[MedicationSavings] = []
    total_savings = 0.0
    total_current = 0.0

    for pm in patient_meds:
        key = normalize_medication_name(pm.name)
        mask = df["medication"].astype(str).str.lower() == key
        if pm.strength and "strength" in df.columns:
            mask &= df["strength"].astype(str).str.lower() == pm.strength.lower()
        group = df[mask]
        if group.empty:
            continue
        med = analyze_medication(
            group,
            current_pharmacy=pm.current_pharmacy,
            on_brand=pm.on_brand,
            has_commercial_insurance=pm.has_commercial_insurance,
        )
        if med:
            results.append(med)
            total_savings += med.recommended_annual_savings
            total_current += med.baseline_price * med.fills_per_year

    return PatientPlan(
        medications=results,
        total_annual_savings=round(total_savings, 2),
        total_current_annual_cost=round(total_current, 2),
    )


if __name__ == "__main__":
    # Quick smoke test against whatever data is present.
    for m in analyze_all():
        top = m.top_opportunity
        headline = f"{top.title} (${top.annual_savings:.0f}/yr)" if top else "no opportunity"
        print(f"[{m.savings_score:5.1f}] {m.medication} {m.strength}: {headline}")
