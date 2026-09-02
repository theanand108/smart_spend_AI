"""Evaluate the learned semantic layer against the frozen V3 benchmark.

This intentionally evaluates `learned_semantic_evidence` only. It does not
exercise merchant mappings, history, amount signals, or transaction-intelligence
policy, so model-language performance can be measured independently.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.intelligence.semantic_ml import learned_semantic_evidence

BENCHMARK = ROOT / "data" / "v3_semantic_benchmark.csv"


def _load_cases() -> list[dict[str, str]]:
    with BENCHMARK.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    cases = _load_cases()
    total = len(cases)
    correct = 0
    resolved_total = 0
    resolved_correct = 0
    unknown_total = 0
    unknown_correct = 0
    by_case_type: dict[str, list[int]] = {}
    errors: list[dict[str, object]] = []
    coverage_resolved = 0

    for case in cases:
        expected = case["expected_category"]
        result = learned_semantic_evidence(case["note"])
        predicted = result["category"] or "Unknown"
        confidence = float(result["confidence"])
        margin = float(result["margin"])
        candidates = result.get("candidates", [])

        is_correct = predicted == expected
        correct += int(is_correct)
        stats = by_case_type.setdefault(case["case_type"], [0, 0])
        stats[0] += int(is_correct)
        stats[1] += 1

        if expected == "Unknown":
            unknown_total += 1
            unknown_correct += int(is_correct)
        else:
            resolved_total += 1
            resolved_correct += int(is_correct)
            coverage_resolved += int(result["category"] is not None)

        if not is_correct:
            errors.append(
                {
                    "id": case["id"],
                    "expected": expected,
                    "predicted": predicted,
                    "note": case["note"],
                    "confidence": confidence,
                    "margin": margin,
                    "candidates": candidates,
                }
            )

    coverage = coverage_resolved / resolved_total if resolved_total else 0.0

    print(f"V3 semantic benchmark: {total} cases")
    print(f"Overall accuracy: {correct / total:.1%} ({correct}/{total})")
    print(
        f"Known-category accuracy: {resolved_correct / resolved_total:.1%} "
        f"({resolved_correct}/{resolved_total})"
    )
    print(
        f"Unknown recall: {unknown_correct / unknown_total:.1%} "
        f"({unknown_correct}/{unknown_total})"
    )
    print(f"Known-category coverage: {coverage:.1%}")
    print()
    print("Accuracy by case type:")
    for case_type, (hits, count) in sorted(by_case_type.items()):
        print(f"  {case_type}: {hits / count:.1%} ({hits}/{count})")

    if errors:
        print()
        print(f"Failures: {len(errors)}")
        for error in errors:
            candidates = error["candidates"] or []
            candidate_text = ", ".join(
                f"{category}={probability:.3f}"
                for category, probability in candidates
            )
            print(
                f"  #{error['id']}: expected={error['expected']!r} "
                f"predicted={error['predicted']!r} "
                f"confidence={error['confidence']:.3f} "
                f"margin={error['margin']:.3f} "
                f"top3=[{candidate_text}] "
                f"note={error['note']!r}"
            )
    else:
        print("Failures: 0")


if __name__ == "__main__":
    main()
