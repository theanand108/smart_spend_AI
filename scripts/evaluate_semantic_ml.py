"""Evaluate a small supervised NLP baseline on held-out semantic notes.

This experiment deliberately keeps the ML model separate from transaction
decision-making. The model predicts semantic purpose from the note only.
The existing intelligence layer remains responsible for confidence, history,
conflicts, and user confirmation.

The dataset has explicit train/test rows so evaluation does not reuse the
100-case transaction benchmark.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATASET = ROOT / "data" / "semantic_intent_dataset.csv"


def main() -> None:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
        from sklearn.pipeline import Pipeline
    except ImportError as exc:
        raise SystemExit(
            "scikit-learn is required for this experiment. "
            "Install it in the project virtualenv with: pip install scikit-learn"
        ) from exc

    with DATASET.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    train = [row for row in rows if row["split"] == "train"]
    test = [row for row in rows if row["split"] == "test"]

    if not train or not test:
        raise SystemExit("Dataset must contain both train and test rows.")

    train_notes = [row["note"] for row in train]
    train_labels = [row["label"] for row in train]
    test_notes = [row["note"] for row in test]
    test_labels = [row["label"] for row in test]

    model = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    model.fit(train_notes, train_labels)
    predictions = model.predict(test_notes)

    accuracy = accuracy_score(test_labels, predictions)
    macro_f1 = f1_score(test_labels, predictions, average="macro")

    print("Semantic NLP Baseline")
    print("=" * 60)
    print(f"Training examples:         {len(train)}")
    print(f"Held-out test examples:    {len(test)}")
    print(f"Classes:                   {len(set(train_labels))}")
    print(f"Test accuracy:             {accuracy:.1%}")
    print(f"Test macro F1:             {macro_f1:.3f}")
    print()
    print("Classification report")
    print("-" * 60)
    print(classification_report(test_labels, predictions, digits=3, zero_division=0))

    print("Confusion matrix labels")
    print("-" * 60)
    labels = sorted(set(train_labels) | set(test_labels))
    matrix = confusion_matrix(test_labels, predictions, labels=labels)
    print(", ".join(labels))
    for label, values in zip(labels, matrix):
        print(f"{label}: {values.tolist()}")

    print()
    print("Held-out predictions")
    print("-" * 60)
    for row, prediction in zip(test, predictions):
        status = "OK" if prediction == row["label"] else "MISS"
        print(f"[{status}] {row['note']!r} -> {prediction} (expected {row['label']})")


if __name__ == "__main__":
    main()
