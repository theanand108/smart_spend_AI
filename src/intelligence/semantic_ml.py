"""Small supervised NLP model for transaction-note semantics.

The model is intentionally an evidence source, not the final transaction
decision-maker. It learns from the labeled semantic-intent dataset and can
abstain when its top prediction is not sufficiently separated from the runner-up.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

DATASET = Path(__file__).resolve().parents[2] / "data" / "semantic_intent_dataset.csv"


def _load_training_rows() -> tuple[list[str], list[str]]:
    with DATASET.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == "train"]
    return [row["note"] for row in rows], [row["label"] for row in rows]


@lru_cache(maxsize=1)
def _build_model() -> Any:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    notes, labels = _load_training_rows()

    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    analyzer="word",
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
    ).fit(notes, labels)


def learned_semantic_evidence(
    note: str | None,
    *,
    min_confidence: float = 0.72,
    min_margin: float = 0.18,
) -> dict[str, Any]:
    """Return a learned semantic candidate, or abstain.

    The abstention threshold is deliberate: a model that is unsure should not
    invent a category. This keeps ML useful without turning its probability
    estimate into an unconditional business rule.
    """
    text = str(note or "").strip()
    if not text:
        return {
            "category": None,
            "confidence": 0.0,
            "margin": 0.0,
            "candidates": [],
            "reason": "No note provided.",
        }

    try:
        model = _build_model()
        probabilities = model.predict_proba([text])[0]
        classes = model.classes_
    except ImportError:
        return {
            "category": None,
            "confidence": 0.0,
            "margin": 0.0,
            "candidates": [],
            "reason": "scikit-learn is not installed; learned semantic evidence is unavailable.",
        }

    ranked = sorted(
        zip(classes, probabilities),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    top_category, top_probability = ranked[0]
    second_probability = float(ranked[1][1]) if len(ranked) > 1 else 0.0
    margin = float(top_probability) - second_probability

    candidates = [(str(category), round(float(probability), 3)) for category, probability in ranked[:3]]

    if float(top_probability) < min_confidence or margin < min_margin:
        return {
            "category": None,
            "confidence": round(float(top_probability), 3),
            "margin": round(margin, 3),
            "candidates": candidates,
            "reason": "Learned model is not confident or sufficiently separated; abstaining.",
        }

    return {
        "category": str(top_category),
        "confidence": round(float(top_probability), 3),
        "margin": round(margin, 3),
        "candidates": candidates,
        "reason": f"Learned NLP model predicts {top_category} from transaction-note language.",
    }
