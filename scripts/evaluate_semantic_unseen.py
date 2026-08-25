"""Evaluate the semantic NLP stack against an independent unseen CSV.

The unseen CSV must contain ``label`` and ``note`` columns. It should not be
added to the training dataset.

The report deliberately separates three views:
1. Raw ML: forced Logistic Regression predictions (the old benchmark).
2. Abstention-aware ML: the production confidence/margin gate can return
   Unknown instead of forcing a weak prediction.
3. Full semantic layer: purpose overrides + deterministic patterns + learned
   semantic evidence, with abstention represented as Unknown.

Usage:
    python scripts/evaluate_semantic_unseen.py path/to/unseen.csv

Optional CSV columns such as ``source`` or ``scenario`` are ignored.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.intelligence.semantic import semantic_note_evidence
from src.intelligence.semantic_ml import _build_model, learned_semantic_evidence

UNKNOWN = "Unknown"


def _accuracy(labels: list[str], predictions: list[str]) -> float:
    if not labels:
        return 0.0
    return sum(expected == predicted for expected, predicted in zip(labels, predictions)) / len(labels)


def _known_accuracy(labels: list[str], predictions: list[str]) -> float:
    pairs = [
        (expected, predicted)
        for expected, predicted in zip(labels, predictions)
        if expected != UNKNOWN
    ]
    if not pairs:
        return 0.0
    return sum(expected == predicted for expected, predicted in pairs) / len(pairs)


def _unknown_recall(labels: list[str], predictions: list[str]) -> float:
    unknown_indices = [index for index, label in enumerate(labels) if label == UNKNOWN]
    if not unknown_indices:
        return 0.0
    return sum(predictions[index] == UNKNOWN for index in unknown_indices) / len(unknown_indices)


def _coverage(predictions: list[str]) -> float:
    if not predictions:
        return 0.0
    return sum(prediction != UNKNOWN for prediction in predictions) / len(predictions)


def _print_stack_summary(name: str, labels: list[str], predictions: list[str]) -> None:
    total = len(labels)
    abstentions = sum(prediction == UNKNOWN for prediction in predictions)
    print(name)
    print("-" * 64)
    print(f"Accuracy:                   {_accuracy(labels, predictions):.1%}")
    print(f"Known-category accuracy:   {_known_accuracy(labels, predictions):.1%}")
    print(f"Unknown recall:             {_unknown_recall(labels, predictions):.1%}")
    print(f"Coverage:                   {_coverage(predictions):.1%}")
    print(f"Abstentions / Unknown:      {abstentions}/{total}")
    print()


def main() -> None:
    from sklearn.metrics import classification_report, confusion_matrix, f1_score

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python scripts/evaluate_semantic_unseen.py path/to/unseen.csv"
        )

    dataset = Path(sys.argv[1]).expanduser().resolve()
    if not dataset.exists():
        raise SystemExit(f"Unseen dataset not found: {dataset}")

    with dataset.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise SystemExit("Unseen dataset is empty.")

    required = {"label", "note"}
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(
            "Unseen dataset must contain columns: label,note. "
            f"Missing: {', '.join(sorted(missing))}"
        )

    notes = [str(row["note"]).strip() for row in rows]
    labels = [str(row["label"]).strip() for row in rows]
    if any(not note for note in notes):
        raise SystemExit("Unseen dataset contains an empty note.")

    model = _build_model()
    raw_predictions = [str(prediction) for prediction in model.predict(notes)]

    learned_predictions: list[str] = []
    full_semantic_predictions: list[str] = []
    learned_abstentions = 0
    semantic_abstentions = 0

    for note in notes:
        learned = learned_semantic_evidence(note)
        learned_category = learned.get("category")
        if learned_category:
            learned_predictions.append(str(learned_category))
        else:
            learned_predictions.append(UNKNOWN)
            learned_abstentions += 1

        semantic = semantic_note_evidence(note)
        semantic_category = semantic.get("category")
        if semantic_category:
            full_semantic_predictions.append(str(semantic_category))
        else:
            full_semantic_predictions.append(UNKNOWN)
            semantic_abstentions += 1

    raw_macro_f1 = f1_score(labels, raw_predictions, average="macro", zero_division=0)
    learned_macro_f1 = f1_score(labels, learned_predictions, average="macro", zero_division=0)
    semantic_macro_f1 = f1_score(
        labels, full_semantic_predictions, average="macro", zero_division=0
    )

    print("Smart Spend AI — Independent Unseen Semantic Evaluation")
    print("=" * 64)
    print(f"Unseen examples:           {len(rows)}")
    print(f"Classes represented:       {len(set(labels))}")
    print()

    print("CHECKPOINT — WHICH LAYER ACTUALLY IMPROVES THE RESULT?")
    print("=" * 64)
    _print_stack_summary("RAW ML (forced prediction)", labels, raw_predictions)
    _print_stack_summary(
        "ABSTENTION-AWARE ML (confidence + margin gate)",
        labels,
        learned_predictions,
    )
    _print_stack_summary(
        "FULL SEMANTIC LAYER (rules + ML + abstention)",
        labels,
        full_semantic_predictions,
    )

    print("Macro F1 comparison")
    print("-" * 64)
    print(f"Raw ML:                     {raw_macro_f1:.3f}")
    print(f"Abstention-aware ML:        {learned_macro_f1:.3f}")
    print(f"Full semantic layer:        {semantic_macro_f1:.3f}")
    print()
    print(f"Learned ML abstentions:     {learned_abstentions}/{len(rows)}")
    print(f"Full semantic abstentions:  {semantic_abstentions}/{len(rows)}")
    print()

    print("Expected class distribution")
    print("-" * 64)
    for label, count in sorted(Counter(labels).items()):
        print(f"{label}: {count}")

    # Keep the original raw-ML report for direct comparison with the previous
    # 82.0% benchmark.
    print()
    print("RAW ML classification report")
    print("-" * 64)
    print(classification_report(labels, raw_predictions, digits=3, zero_division=0))

    print("Raw ML confusion matrix")
    print("-" * 64)
    class_labels = sorted(set(labels) | set(raw_predictions))
    matrix = confusion_matrix(labels, raw_predictions, labels=class_labels)
    header = "Expected \\ Predicted".ljust(24) + " ".join(
        f"{label[:12]:>12}" for label in class_labels
    )
    print(header)
    for label, row_values in zip(class_labels, matrix):
        values = " ".join(f"{int(value):>12}" for value in row_values)
        print(f"{label[:23].ljust(24)}{values}")

    print()
    print("Raw ML top misclassification pairs")
    print("-" * 64)
    pair_counts = Counter(
        (expected, predicted)
        for expected, predicted in zip(labels, raw_predictions)
        if expected != predicted
    )
    if pair_counts:
        for (expected, predicted), count in pair_counts.most_common():
            print(f"{count:>3}  {expected} -> {predicted}")
    else:
        print("No misclassifications.")

    print()
    print("Unseen predictions")
    print("-" * 64)
    misses = 0
    for row, raw, learned, semantic in zip(
        rows, raw_predictions, learned_predictions, full_semantic_predictions
    ):
        expected = row["label"]
        status = "OK" if semantic == expected else "MISS"
        if status == "MISS":
            misses += 1
        print(
            f"[{status}] {row['note']!r} -> "
            f"raw={raw}; abstention_ml={learned}; full_semantic={semantic} "
            f"(expected {expected})"
        )

    print()
    print(f"Full semantic misses:       {misses}/{len(rows)}")

    raw_accuracy = _accuracy(labels, raw_predictions)
    semantic_accuracy = _accuracy(labels, full_semantic_predictions)
    delta = semantic_accuracy - raw_accuracy
    print()
    print("CHECKPOINT DECISION")
    print("-" * 64)
    if delta > 0:
        print(f"Promising: full semantic accuracy improved by {delta:+.1%} over raw ML.")
        print("Next step: inspect remaining semantic misses before retraining.")
    elif delta == 0:
        print("No accuracy gain yet, but inspect Unknown recall and coverage before changing the model.")
    else:
        print(f"Full semantic accuracy changed by {delta:+.1%}; do not retrain blindly.")
        print("Next step: inspect whether abstention is trading accuracy for safer decisions.")


if __name__ == "__main__":
    main()
