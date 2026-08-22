"""Evaluate Smart Spend AI's current V1 transaction categorization baseline.

The benchmark dataset is synthetic and intentionally exercises both obvious
merchant names and ambiguous/context-dependent UPI-style transactions.
This script does not change application behavior.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import categorize  # noqa: E402

DATASET = ROOT / "data" / "transaction_intelligence_eval.csv"


def main() -> None:
    if not DATASET.exists():
        raise SystemExit(f"Benchmark dataset not found: {DATASET}")

    with DATASET.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    total = len(rows)
    correct = 0
    unknown_expected = 0
    unknown_correct = 0
    false_confidence = 0
    scenario_matches: dict[str, list[bool]] = defaultdict(list)
    mismatches: list[tuple[str, str, str, str]] = []

    for row in rows:
        predicted = categorize(row["merchant_name"])
        expected = row["expected_category_v2"]
        is_unknown_expected = expected == "Unknown"
        is_unknown_predicted = predicted == "Others"

        correct_match = predicted == expected
        unknown_match = is_unknown_expected == is_unknown_predicted

        correct += int(correct_match)
        unknown_expected += int(is_unknown_expected)
        unknown_correct += int(unknown_match)
        false_confidence += int(is_unknown_expected and not is_unknown_predicted)
        scenario_matches[row["scenario"]].append(correct_match)

        if not correct_match:
            mismatches.append(
                (row["case_id"], row["scenario"], expected, predicted)
            )

    print("Transaction Intelligence — V1 Baseline")
    print("=" * 50)
    print(f"Cases:                  {total}")
    print(f"Category accuracy:      {correct / total:.1%}")
    print(f"Unknown detection:      {unknown_correct / total:.1%}")
    print(f"Expected unknown:       {unknown_expected}")
    print(f"False-confidence:       {false_confidence}")
    print()

    print("Accuracy by scenario")
    print("-" * 50)
    for scenario, matches in sorted(scenario_matches.items()):
        print(f"{scenario:36} {sum(matches) / len(matches):.1%}")

    print()
    print(f"Category mismatches: {len(mismatches)}")
    if mismatches:
        predicted_counts = Counter(predicted for _, _, _, predicted in mismatches)
        print("Most common V1 predictions among mismatches:")
        for category, count in predicted_counts.most_common():
            print(f"  {category}: {count}")

        print()
        print("First 20 mismatches:")
        for case_id, scenario, expected, predicted in mismatches[:20]:
            print(f"  {case_id}: {scenario} | expected={expected} | predicted={predicted}")


if __name__ == "__main__":
    main()
