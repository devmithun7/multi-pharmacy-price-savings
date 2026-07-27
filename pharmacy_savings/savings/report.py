"""
Command-line reporting for the patient-savings engine.

Run with:  python -m pharmacy_savings.savings.report [options]

Examples
--------
Rank every medication in the collected price data by savings potential:

    python -m pharmacy_savings.savings.report

Optimize a specific patient's regimen from a JSON profile:

    python -m pharmacy_savings.savings.report --patient data/patient_profile_example.json

Point at a different data file, or emit machine-readable JSON:

    python -m pharmacy_savings.savings.report --data data/price_data_large.csv --json

Validate the engine end-to-end against the bundled sample:

    python -m pharmacy_savings.savings.report --selftest
"""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from ..utils import load_existing_data
from ..paths import SAMPLE_PRICE_CSV
from .engine import (
    analyze_all,
    optimize_patient,
    PatientMedication,
    MedicationSavings,
)

BAR = "=" * 68
SUB = "-" * 68


def _score_bar(score: float, width: int = 20) -> str:
    filled = int(round(score / 100 * width))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def print_medication(med: MedicationSavings, indent: str = "") -> None:
    print(f"{indent}{med.medication} {med.strength}  "
          f"({med.drug_type}, {med.category}, "
          f"{'chronic' if med.chronic else 'acute'})")
    print(f"{indent}  Savings Score: {med.savings_score:5.1f} "
          f"{_score_bar(med.savings_score)}   "
          f"recommended: ${med.recommended_annual_savings:,.0f}/yr "
          f"(up to ${med.max_annual_savings:,.0f}/yr)")
    print(f"{indent}  Currently ~${med.baseline_price:.2f}/fill | "
          f"cheapest seen ${med.best_observed_price:.2f} at "
          f"{med.best_observed_pharmacy} | spread ${med.price_spread:.2f}")
    if not med.opportunities:
        print(f"{indent}  (no material savings opportunities found)")
        return
    for opp in sorted(med.opportunities, key=lambda o: o.score, reverse=True):
        print(f"{indent}   - [{opp.score:5.1f}] {opp.title}: "
              f"${opp.baseline_price:.2f} -> ${opp.optimized_price:.2f} "
              f"(save ${opp.per_fill_savings:.2f}/fill, "
              f"${opp.annual_savings:,.0f}/yr)")
        print(f"{indent}       {opp.detail}")


def run_overview(df: pd.DataFrame, as_json: bool) -> None:
    results = analyze_all(df)
    if not results:
        print("No price data found. Collect prices first (see README).")
        return

    if as_json:
        payload = [
            {
                "medication": m.medication,
                "strength": m.strength,
                "drug_type": m.drug_type,
                "category": m.category,
                "savings_score": m.savings_score,
                "recommended_annual_savings": m.recommended_annual_savings,
                "max_annual_savings": m.max_annual_savings,
                "baseline_price": m.baseline_price,
                "best_observed_price": m.best_observed_price,
                "best_observed_pharmacy": m.best_observed_pharmacy,
                "opportunities": [o.as_dict() for o in m.opportunities],
            }
            for m in results
        ]
        print(json.dumps(payload, indent=2))
        return

    print(BAR)
    print("PATIENT SAVINGS REPORT  (ranked by Savings Score)")
    print(BAR)
    total = sum(m.recommended_annual_savings for m in results)
    print(f"Medications analyzed: {len(results)}   "
          f"Total recommended savings: ${total:,.0f}/yr\n")
    for med in results:
        print_medication(med)
        print(SUB)


def _load_patient(path: str) -> tuple[str, list[PatientMedication]]:
    with open(path, "r", encoding="utf-8") as f:
        profile = json.load(f)
    name = profile.get("name", "Patient")
    default_pharmacy = profile.get("default_pharmacy")
    default_insurance = bool(profile.get("has_commercial_insurance", False))
    meds = []
    for m in profile.get("medications", []):
        meds.append(PatientMedication(
            name=m["name"],
            strength=m.get("strength", ""),
            current_pharmacy=m.get("current_pharmacy", default_pharmacy),
            on_brand=bool(m.get("on_brand", False)),
            has_commercial_insurance=bool(
                m.get("has_commercial_insurance", default_insurance)),
        ))
    return name, meds


def run_patient(df: pd.DataFrame, path: str, as_json: bool) -> None:
    name, meds = _load_patient(path)
    plan = optimize_patient(meds, df)

    if not plan.medications:
        print(f"No matching price data for {name}'s medications. "
              "Check the names/strengths against the collected data.")
        return

    if as_json:
        payload = {
            "patient": name,
            "total_annual_savings": plan.total_annual_savings,
            "total_current_annual_cost": plan.total_current_annual_cost,
            "medications": [
                {
                    "medication": m.medication,
                    "strength": m.strength,
                    "savings_score": m.savings_score,
                    "recommended_annual_savings": m.recommended_annual_savings,
                    "max_annual_savings": m.max_annual_savings,
                    "top_action": m.top_opportunity.title if m.top_opportunity else None,
                    "opportunities": [o.as_dict() for o in m.opportunities],
                }
                for m in plan.prioritized
            ],
        }
        print(json.dumps(payload, indent=2))
        return

    print(BAR)
    print(f"SAVINGS ACTION PLAN FOR: {name}")
    print(BAR)
    pct = (plan.total_annual_savings / plan.total_current_annual_cost * 100
           if plan.total_current_annual_cost else 0)
    print(f"Estimated current spend: ${plan.total_current_annual_cost:,.0f}/yr")
    print(f"Potential savings:       ${plan.total_annual_savings:,.0f}/yr "
          f"(~{pct:.0f}% of current spend)\n")
    print("Tackle these in order of impact:\n")

    for rank, med in enumerate(plan.prioritized, start=1):
        top = med.top_opportunity
        if not top:
            continue
        print(f"{rank}. {med.medication} {med.strength}  "
              f"-> save ${med.recommended_annual_savings:,.0f}/yr "
              f"(score {med.savings_score:.0f})")
        print(f"     ACTION: {top.title}")
        print(f"     {top.detail}")
        others = [o for o in sorted(med.opportunities, key=lambda o: o.annual_savings, reverse=True)
                  if o is not top][:2]
        for o in others:
            print(f"       also: {o.title} (${o.annual_savings:,.0f}/yr)")
        print()


def run_selftest() -> int:
    """
    Validate the engine end-to-end against the bundled sample dataset.

    Prints PASS/FAIL for each expected behavior and returns 0 only if every
    check passes. No external data or network needed.
    """
    df = load_existing_data(SAMPLE_PRICE_CSV)
    if df is None or df.empty:
        print(f"SELFTEST ERROR: could not load {SAMPLE_PRICE_CSV}")
        return 1

    results = analyze_all(df)
    by_name = {m.medication.lower(): m for m in results}
    checks: list[tuple[str, bool, str]] = []

    def check(label: str, ok: bool, note: str = "") -> None:
        checks.append((label, bool(ok), note))

    # 1. All sample medications were analyzed.
    expected = {"lipitor", "atorvastatin", "metformin", "lisinopril",
                "sertraline", "levothyroxine", "amoxicillin"}
    found = set(by_name)
    check("all sample medications analyzed",
          expected.issubset(found),
          f"missing: {sorted(expected - found)}")

    # 2. Brand detection: Lipitor is classified as a brand.
    lip = by_name.get("lipitor")
    check("Lipitor detected as brand", bool(lip) and lip.drug_type == "brand",
          f"got drug_type={getattr(lip, 'drug_type', None)}")

    # 3. Without insurance, the recommended Lipitor action is the generic switch
    #    (the copay coupon requires commercial insurance and is excluded).
    check("Lipitor recommends generic switch (no insurance context)",
          bool(lip) and lip.top_opportunity is not None
          and lip.top_opportunity.lever == "generic_switch",
          f"got lever={lip.top_opportunity.lever if lip and lip.top_opportunity else None}")

    # 4. The brand (Lipitor) is the highest-scoring opportunity overall.
    check("Lipitor is the top-ranked medication",
          bool(results) and results[0].medication.lower() == "lipitor",
          f"top was {results[0].medication if results else None}")

    # 5. The acute antibiotic ranks below every chronic med (recurrence matters).
    amox = by_name.get("amoxicillin")
    chronic_scores = [m.savings_score for m in results if m.chronic]
    check("acute Amoxicillin scores below all chronic meds",
          bool(amox) and all(amox.savings_score < s for s in chronic_scores),
          f"amoxicillin={getattr(amox, 'savings_score', None)}")

    # 6. Pharmacy-switch savings are computed from the observed spread.
    met = by_name.get("metformin")
    check("Metformin finds a cheaper pharmacy than baseline",
          bool(met) and met.best_observed_price < met.baseline_price,
          f"best={getattr(met, 'best_observed_price', None)} "
          f"baseline={getattr(met, 'baseline_price', None)}")

    # 7. Patient context changes the recommendation: with commercial insurance,
    #    Lipitor should recommend the manufacturer copay card.
    plan = optimize_patient(
        [PatientMedication("Lipitor", "20mg", current_pharmacy="CVS",
                           on_brand=True, has_commercial_insurance=True)],
        df,
    )
    lip_ins = plan.medications[0] if plan.medications else None
    check("Lipitor recommends copay card when insured",
          bool(lip_ins) and lip_ins.top_opportunity is not None
          and lip_ins.top_opportunity.lever == "manufacturer_coupon",
          f"got lever={lip_ins.top_opportunity.lever if lip_ins and lip_ins.top_opportunity else None}")

    print("=" * 68)
    print("SAVINGS ENGINE SELF-TEST")
    print("=" * 68)
    passed = 0
    for label, ok, note in checks:
        status = "PASS" if ok else "FAIL"
        line = f"[{status}] {label}"
        if not ok and note:
            line += f"  ({note})"
        print(line)
        passed += int(ok)
    print("-" * 68)
    print(f"{passed}/{len(checks)} checks passed")
    return 0 if passed == len(checks) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rank prescription savings opportunities.")
    parser.add_argument("--patient", help="Path to a patient profile JSON file.")
    parser.add_argument("--data", help="Path to a price CSV (defaults to data/price_data.csv).")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report.")
    parser.add_argument("--selftest", action="store_true",
                        help="Validate the engine against the bundled sample data.")
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    df = load_existing_data(args.data) if args.data else load_existing_data()
    if df is None or df.empty:
        print("No price data found. Collect prices first (see README).")
        return 1

    if args.patient:
        run_patient(df, args.patient, args.json)
    else:
        run_overview(df, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
