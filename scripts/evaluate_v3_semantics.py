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
THRESHOLDS = (0.70, 0.60, 0.55, 0.50, 0.45, 0.40, 0.35)
MARGIN_THRESHOLDS = (0.35, 0.25, 0.20, 0.18, 0.15, 0.10, 0.05, 0.00)


def _load_cases() -> list[dict[str, str]]:
    with BENCHMARK.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _hypothetical_prediction(
    result: dict[str, object],
    confidence_threshold: float,
    margin_threshold: float = 0.0,
) -> str:
    """Apply hypothetical confidence + margin gates to raw top-1 output."""
    candidates = result.get("candidates", [])
    if not candidates:
        return "Unknown"

    top_category, top_probability = candidates[0]
    margin = (
        float(top_probability) - float(candidates[1][1])
        if len(candidates) > 1
        else float(top_probability)
    )
    if (
        top_category == "Unknown"
        or float(top_probability) < confidence_threshold
        or margin < margin_threshold
    ):
        return "Unknown"
    return str(top_category)


def _evaluate_threshold(
    cases: list[dict[str, str]],
    results: list[dict[str, object]],
    threshold: float,
) -> dict[str, float | int]:
    total = len(cases)
    correct = 0
    known_total = 0
    known_correct = 0
    known_accepted = 0
    unknown_total = 0
    unknown_correct = 0
    false_positives = 0

    for case, result in zip(cases, results):
        expected = case["expected_category"]
        predicted = _hypothetical_prediction(result, threshold)
        is_correct = predicted == expected
        correct += int(is_correct)

        if expected == "Unknown":
            unknown_total += 1
            unknown_correct += int(is_correct)
            false_positives += int(predicted != "Unknown")
        else:
            known_total += 1
            known_correct += int(is_correct)
            known_accepted += int(predicted != "Unknown")

    return {
        "threshold": threshold,
        "accuracy": correct / total if total else 0.0,
        "known_coverage": known_accepted / known_total if known_total else 0.0,
        "known_accuracy": known_correct / known_total if known_total else 0.0,
        "accepted_accuracy": (
            known_correct / known_accepted if known_accepted else 0.0
        ),
        "unknown_recall": unknown_correct / unknown_total if unknown_total else 0.0,
        "false_positives": false_positives,
        "recoverable_failures": sum(
            1
            for case, result in zip(cases, results)
            if case["expected_category"] != "Unknown"
            and case["expected_category"]
            == _hypothetical_prediction(result, threshold)
        ),
    }


def _evaluate_matrix(
    cases: list[dict[str, str]],
    results: list[dict[str, object]],
) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for confidence_threshold in THRESHOLDS:
        for margin_threshold in MARGIN_THRESHOLDS:
            total = len(cases)
            correct = 0
            known_total = 0
            known_correct = 0
            known_accepted = 0
            unknown_total = 0
            unknown_correct = 0
            false_positives = 0

            for case, result in zip(cases, results):
                expected = case["expected_category"]
                predicted = _hypothetical_prediction(
                    result, confidence_threshold, margin_threshold
                )
                is_correct = predicted == expected
                correct += int(is_correct)

                if expected == "Unknown":
                    unknown_total += 1
                    unknown_correct += int(is_correct)
                    false_positives += int(predicted != "Unknown")
                else:
                    known_total += 1
                    known_correct += int(is_correct)
                    known_accepted += int(predicted != "Unknown")

            rows.append(
                {
                    "confidence": confidence_threshold,
                    "margin": margin_threshold,
                    "accuracy": correct / total if total else 0.0,
                    "known_coverage": known_accepted / known_total
                    if known_total
                    else 0.0,
                    "known_accuracy": known_correct / known_total
                    if known_total
                    else 0.0,
                    "accepted_accuracy": known_correct / known_accepted
                    if known_accepted
                    else 0.0,
                    "unknown_recall": unknown_correct / unknown_total
                    if unknown_total
                    else 0.0,
                    "false_positives": false_positives,
                    "recoverable_failures": known_correct,
                }
            )
    return rows


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
    results: list[dict[str, object]] = []

    for case in cases:
        expected = case["expected_category"]
        result = learned_semantic_evidence(case["note"])
        results.append(result)
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

    print()
    print("Offline threshold sweep (raw top-1 probability only):")
    print(
        "  threshold | accuracy | known coverage | known accuracy | "
        "accepted accuracy | unknown recall | false positives | recoverable"
    )
    for threshold in THRESHOLDS:
        metrics = _evaluate_threshold(cases, results, threshold)
        print(
            f"  {threshold:9.2f} | "
            f"{metrics['accuracy']:8.1%} | "
            f"{metrics['known_coverage']:14.1%} | "
            f"{metrics['known_accuracy']:14.1%} | "
            f"{metrics['accepted_accuracy']:17.1%} | "
            f"{metrics['unknown_recall']:14.1%} | "
            f"{metrics['false_positives']:15d} | "
            f"{metrics['recoverable_failures']:10d}"
        )

    matrix = _evaluate_matrix(cases, results)
    print()
    print("Confidence × margin sweep (raw top-1 probability + margin):")
    print(
        "  confidence | margin | accuracy | known coverage | "
        "known accuracy | accepted accuracy | unknown recall | false positives"
    )
    for row in matrix:
        print(
            f"  {row['confidence']:10.2f} | "
            f"{row['margin']:6.2f} | "
            f"{row['accuracy']:8.1%} | "
            f"{row['known_coverage']:14.1%} | "
            f"{row['known_accuracy']:14.1%} | "
            f"{row['accepted_accuracy']:17.1%} | "
            f"{row['unknown_recall']:14.1%} | "
            f"{row['false_positives']:15d}"
        )

    safe_rows = [row for row in matrix if row["false_positives"] == 0]
    if safe_rows:
        best = max(safe_rows, key=lambda row: (row["accuracy"], row["accepted_accuracy"]))
        print()
        print(
            "Best zero-false-positive configuration: "
            f"confidence={best['confidence']:.2f}, margin={best['margin']:.2f}, "
            f"accuracy={best['accuracy']:.1%}, "
            f"known coverage={best['known_coverage']:.1%}, "
            f"accepted accuracy={best['accepted_accuracy']:.1%}"
        )


if __name__ == "__main__":
    main()
