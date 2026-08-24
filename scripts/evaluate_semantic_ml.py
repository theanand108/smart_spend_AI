"""Evaluate Smart Spend AI V2 semantic NLP model on held-out rows."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATASET = ROOT / "data" / "semantic_intent_dataset.csv"


def build_model():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    return Pipeline(
        [
            (
                "features",
                FeatureUnion(
                    [
                        (
                            "word_tfidf",
                            TfidfVectorizer(
                                lowercase=True,
                                analyzer="word",
                                ngram_range=(1, 2),
                                min_df=1,
                                sublinear_tf=True,
                            ),
                        ),
                        (
                            "char_tfidf",
                            TfidfVectorizer(
                                lowercase=True,
                                analyzer="char_wb",
                                ngram_range=(3, 5),
                                min_df=1,
                                sublinear_tf=True,
                            ),
                        ),
                    ]
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


def main():
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        f1_score,
    )

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

    model = build_model().fit(train_notes, train_labels)
    predictions = model.predict(test_notes)

    accuracy = accuracy_score(test_labels, predictions)
    macro_f1 = f1_score(test_labels, predictions, average="macro")

    print("Semantic NLP V2")
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

    print()
    print("Held-out predictions")
    print("-" * 60)

    for row, prediction in zip(test, predictions):
        status = "OK" if prediction == row["label"] else "MISS"
        print(
            f"[{status}] {row['note']!r} -> "
            f"{prediction} (expected {row['label']})"
        )


if __name__ == "__main__":
    main()
