"""Smart Spend AI V2 semantic NLP model.

Uses word TF-IDF plus character TF-IDF with Logistic Regression.
Character n-grams improve robustness to short/informal notes and small
spelling variations without adding a separate spell-correction system.
The model remains an evidence source and can abstain.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data" / "semantic_intent_dataset.csv"
AUGMENTATION_DATASET = ROOT / "data" / "semantic_intent_augmentation_v21.csv"


def _load_rows(path: Path, *, train_only: bool = False) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if train_only:
        rows = [r for r in rows if r["split"] == "train"]
    return rows


def _load_training_rows() -> tuple[list[str], list[str]]:
    rows = _load_rows(DATASET, train_only=True)
    if AUGMENTATION_DATASET.exists():
        rows.extend(_load_rows(AUGMENTATION_DATASET))
    return [r["note"] for r in rows], [r["label"] for r in rows]


@lru_cache(maxsize=1)
def _build_model() -> Any:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    notes, labels = _load_training_rows()

    features = FeatureUnion(
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
    )

    return Pipeline(
        [
            ("features", features),
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

    candidates = [
        (str(category), round(float(probability), 3))
        for category, probability in ranked[:3]
    ]

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
