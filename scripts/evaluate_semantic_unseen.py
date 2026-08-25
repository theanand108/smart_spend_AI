"""Evaluate the semantic NLP model against an independent unseen CSV.

The unseen CSV must contain ``label`` and ``note`` columns. It should not be
added to the training dataset. This script imports the production model so the
same word+character TF-IDF pipeline and abstention logic are evaluated.

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

from src.intelligence.semantic_ml import _build_model


def main() -> None:
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

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
    predictions = model.predict(notes)

    accuracy = accuracy_score(labels, predictions)
    macro_f1 = f1_score(labels, predictions, average="macro", zero_division=0)

    print("Smart Spend AI — Independent Unseen Semantic Evaluation")
    print("=" * 64)
    print(f"Unseen examples:           {len(rows)}")
    print(f"Classes represented:       {len(set(labels))}")
    print(f"Accuracy:                   {accuracy:.1%}")
    print(f"Macro F1:                   {macro_f1:.3f}")
    print()
    print("Expected class distribution")
    print("-" * 64)
    for label, count in sorted(Counter(labels).items()):
        print(f"{label}: {count}")

    print()
    print("Classification report")
    print("-" * 64)
    print(classification_report(labels, predictions, digits=3, zero_division=0))

    # Show where the model confuses categories. This is more useful than
    # accuracy alone when auditing a multi-class semantic classifier.
    class_labels = sorted(set(labels) | set(predictions))
    matrix = confusion_matrix(labels, predictions, labels=class_labels)
    print("Confusion matrix")
    print("-" * 64)
    header = "Expected \\ Predicted".ljust(24) + " ".join(
        f"{label[:12]:>12}" for label in class_labels
    )
    print(header)
    for label, row_values in zip(class_labels, matrix):
        values = " ".join(f"{int(value):>12}" for value in row_values)
        print(f"{label[:23].ljust(24)}{values}")

    print()
    print("Top misclassification pairs")
    print("-" * 64)
    pair_counts = Counter(
        (expected, predicted)
        for expected, predicted in zip(labels, predictions)
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
    for row, prediction in zip(rows, predictions):
        expected = row["label"]
        status = "OK" if prediction == expected else "MISS"
        if status == "MISS":
            misses += 1
        print(f"[{status}] {row['note']!r} -> {prediction} (expected {expected})")

    print()
    print(f"Misses:                     {misses}/{len(rows)}")


if __name__ == "__main__":
    main()
