"""Compare Smart Spend AI V1 and V2 transaction categorization.

The benchmark dataset is synthetic and intentionally exercises both obvious
merchant names and ambiguous/context-dependent UPI-style transactions.
This script does not change application behavior.
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
        amount=float(row["amount"]),
        note=row["note"],
        payment_method=row["payment_method"],
        history=history,
    )


def v2_matches_expected(result: dict[str, Any], expected: str) -> bool:
    if expected == "Unknown":
        return result["status"] in {"unknown", "conflict"} and result["category"] is None
    return result["category"] == expected and not (
        result["status"] == "conflict" and result["needs_user_confirmation"]
    )


def main() -> None:
    if not DATASET.exists():
        raise SystemExit(f"Benchmark dataset not found: {DATASET}")

    with DATASET.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    v1_correct = 0
    v2_correct = 0
    v2_unknown_correct = 0
    v2_false_confidence = 0
    v2_confirmation_cases = 0
    v2_scenario_matches: dict[str, list[bool]] = defaultdict(list)
    v1_scenario_matches: dict[str, list[bool]] = defaultdict(list)
    v2_mismatches: list[tuple[str, str, str, str, str]] = []

    # Build history incrementally so repeated-merchant cases can use earlier
    # benchmark examples without leaking future labels into the prediction.
    history: list[dict[str, Any]] = []

    for row in rows:
        expected = row["expected_category_v2"]
        v1_predicted = categorize(row["merchant_name"])
        v1_match = v1_predicted == expected
        v2_result = v2_prediction(row, history)
        v2_match = v2_matches_expected(v2_result, expected)

        v1_correct += int(v1_match)
        v2_correct += int(v2_match)
        v2_unknown_correct += int(
            expected == "Unknown"
            and v2_result["category"] is None
            and v2_result["status"] in {"unknown", "conflict"}
        )
        v2_false_confidence += int(
            expected == "Unknown" and v2_result["category"] is not None
        )
        v2_confirmation_cases += int(v2_result["needs_user_confirmation"])
        v1_scenario_matches[row["scenario"]].append(v1_match)
        v2_scenario_matches[row["scenario"]].append(v2_match)

        if not v2_match:
            v2_mismatches.append(
                (
                    row["case_id"],
                    row["scenario"],
                    expected,
                    str(v2_result["category"]),
                    str(v2_result["status"]),
                )
            )

        # Only confirmed, non-unknown benchmark outcomes become history.
        # This mirrors the product principle that uncertain guesses should not
        # become permanent merchant memory.
        if expected != "Unknown":
            history.append(
                {
                    "merchant_name": row["merchant_name"],
                    "category": expected,
                }
            )

    total = len(rows)

    print("Transaction Intelligence — V1 vs V2")
    print("=" * 55)
    print(f"Cases:                       {total}")
    print(f"V1 category accuracy:        {v1_correct / total:.1%}")
    print(f"V2 category accuracy:        {v2_correct / total:.1%}")
    print(f"V2 improvement:              {(v2_correct - v1_correct) / total:+.1%}")
    print(f"V2 unknown cases resolved:   {v2_unknown_correct}/{sum(row['expected_category_v2'] == 'Unknown' for row in rows)}")
    print(f"V2 false-confidence cases:   {v2_false_confidence}")
    print(f"V2 confirmation cases:       {v2_confirmation_cases}")
    print()

    print("Accuracy by scenario")
    print("-" * 55)
    scenarios = sorted(set(v1_scenario_matches) | set(v2_scenario_matches))
    for scenario in scenarios:
        v1_matches = v1_scenario_matches[scenario]
        v2_matches = v2_scenario_matches[scenario]
        print(
            f"{scenario:36} "
            f"V1={sum(v1_matches) / len(v1_matches):.1%}  "
            f"V2={sum(v2_matches) / len(v2_matches):.1%}"
        )

    print()
    print(f"V2 mismatches: {len(v2_mismatches)}")
    if v2_mismatches:
        print("First 20 V2 mismatches:")
        for case_id, scenario, expected, predicted, status in v2_mismatches[:20]:
            print(
                f"  {case_id}: {scenario} | expected={expected} | "
                f"predicted={predicted} | status={status}"
            )


if __name__ == "__main__":
    main()
