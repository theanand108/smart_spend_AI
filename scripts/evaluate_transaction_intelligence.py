"""Evaluate Smart Spend AI V1 and V2 transaction intelligence.

The benchmark is synthetic and intentionally exercises obvious merchant names,
ambiguous UPI-style transactions, context, history, and conflicts.

This evaluator keeps two ideas separate:
1. Category correctness: did the system identify the expected category?
2. Decision safety: did it avoid claiming certainty when the benchmark expects
   uncertainty or a conflict confirmation?

The script does not change application behavior.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import categorize  # noqa: E402
from src.intelligence.categorizer import categorize_transaction  # noqa: E402

DATASET = ROOT / "data" / "transaction_intelligence_eval.csv"


def v2_prediction(row: dict[str, str], history: list[dict[str, Any]]) -> dict[str, Any]:
    return categorize_transaction(
        merchant_name=row["merchant_name"],
        amount=float(row["amount_inr"]),
        note=row["note"],
        payment_method=row["payment_method"],
        history=history,
    )


def category_matches(result: dict[str, Any], expected: str) -> bool:
    """Measure category correctness independently from confidence/status."""
    if expected == "Unknown":
        return result["category"] is None
    return result["category"] == expected


def decision_is_safe(result: dict[str, Any], expected: str, scenario: str, expected_action: str) -> bool:
    """Measure whether V2 followed the benchmark's intended user action."""
    if expected == "Unknown":
        return result["category"] is None and result["needs_user_confirmation"]

    if expected_action == "ask_user_if_conflict" or scenario == "same_merchant_conflicting_context":
        return result["category"] == expected and result["needs_user_confirmation"]

    if expected_action in {"ask_user", "ask_user_if_low"}:
        return result["category"] == expected and result["needs_user_confirmation"]

    if expected_action == "categorize_if_supported_else_ask":
        return result["category"] == expected and (
            not result["needs_user_confirmation"] or result["status"] in {"needs_confirmation", "conflict"}
        )

    return result["category"] == expected and not result["needs_user_confirmation"]


def main() -> None:
    if not DATASET.exists():
        raise SystemExit(f"Benchmark dataset not found: {DATASET}")

    with DATASET.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    v1_correct = 0
    v2_category_correct = 0
    v2_decision_safe = 0
    v2_unknown_correct = 0
    v2_false_confidence = 0
    v2_confirmation_cases = 0
    v2_scenario_category: dict[str, list[bool]] = defaultdict(list)
    v2_scenario_decision: dict[str, list[bool]] = defaultdict(list)
    v1_scenario_matches: dict[str, list[bool]] = defaultdict(list)
    v2_mismatches: list[tuple[str, str, str, str, str]] = []

    history: list[dict[str, Any]] = []

    for row in rows:
        expected = row["expected_category_v2"]
        scenario = row["scenario"]
        expected_action = row["expected_action"]
        v1_predicted = categorize(row["merchant_name"])
        v1_match = v1_predicted == expected
        v2_result = v2_prediction(row, history)
        v2_category_match = category_matches(v2_result, expected)
        v2_decision_match = decision_is_safe(v2_result, expected, scenario, expected_action)

        v1_correct += int(v1_match)
        v2_category_correct += int(v2_category_match)
        v2_decision_safe += int(v2_decision_match)
        v2_unknown_correct += int(expected == "Unknown" and v2_category_match)
        v2_false_confidence += int(expected == "Unknown" and v2_result["category"] is not None)
        v2_confirmation_cases += int(v2_result["needs_user_confirmation"])
        v1_scenario_matches[scenario].append(v1_match)
        v2_scenario_category[scenario].append(v2_category_match)
        v2_scenario_decision[scenario].append(v2_decision_match)

        if not v2_category_match:
            v2_mismatches.append((row["case_id"], scenario, expected, str(v2_result["category"]), str(v2_result["status"])))

        if expected != "Unknown":
            # Preserve the full historical transaction context. The V2
            # evidence layer can use amount similarity, so the benchmark must
            # not discard amount information when constructing merchant memory.
            history.append({
                "merchant_name": row["merchant_name"],
                "category": expected,
                "amount": float(row["amount_inr"]),
                "note": row["note"],
                "payment_method": row["payment_method"],
            })

    total = len(rows)
    unknown_total = sum(row["expected_category_v2"] == "Unknown" for row in rows)

    print("Transaction Intelligence — V1 vs V2")
    print("=" * 60)
    print(f"Cases:                       {total}")
    print(f"V1 category accuracy:        {v1_correct / total:.1%}")
    print(f"V2 category accuracy:        {v2_category_correct / total:.1%}")
    print(f"V2 improvement:              {(v2_category_correct - v1_correct) / total:+.1%}")
    print(f"V2 decision safety:          {v2_decision_safe / total:.1%}")
    print(f"V2 unknown cases resolved:   {v2_unknown_correct}/{unknown_total}")
    print(f"V2 false-confidence cases:   {v2_false_confidence}")
    print(f"V2 confirmation cases:       {v2_confirmation_cases}")
    print()

    print("Accuracy by scenario")
    print("-" * 60)
    scenarios = sorted(set(v1_scenario_matches) | set(v2_scenario_category))
    for scenario in scenarios:
        v1_matches = v1_scenario_matches[scenario]
        v2_categories = v2_scenario_category[scenario]
        v2_decisions = v2_scenario_decision[scenario]
        print(f"{scenario:36} V1={sum(v1_matches) / len(v1_matches):.1%}  V2-category={sum(v2_categories) / len(v2_categories):.1%}  V2-decision={sum(v2_decisions) / len(v2_decisions):.1%}")

    print()
    print(f"V2 category mismatches: {len(v2_mismatches)}")
    if v2_mismatches:
        print("First 20 category mismatches:")
        for case_id, scenario, expected, predicted, status in v2_mismatches[:20]:
            print(f"  {case_id}: {scenario} | expected={expected} | predicted={predicted} | status={status}")


if __name__ == "__main__":
    main()
