"""Personalized memory for recurring transaction entities.

An entity can be a person, family member, household contact, or merchant-like
UPI identity. Unlike a fixed merchant mapping, entity memory keeps the full
category distribution and can mark an entity as VARIES when its purpose changes
across transactions.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

IGNORED_CATEGORIES = {None, "", "Unknown", "Others"}


def build_entity_profile(
    entity_name: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build an explainable profile from historical transactions for an entity."""
    normalized = str(entity_name or "").strip().lower()
    transactions = [
        item
        for item in (history or [])
        if str(item.get("merchant_name") or "").strip().lower() == normalized
    ]

    counts: Counter[str] = Counter()
    for item in transactions:
        category = item.get("category")
        if category not in IGNORED_CATEGORIES:
            counts[str(category)] += 1

    total = sum(counts.values())
    if not counts:
        return {
            "entity_name": entity_name,
            "transaction_count": len(transactions),
            "category_counts": {},
            "dominant_category": None,
            "dominance": 0.0,
            "memory_label": "UNKNOWN",
        }

    dominant_category, dominant_count = counts.most_common(1)[0]
    dominance = dominant_count / total

    # Three or more categories with no clear dominant purpose means the entity
    # should not be treated like a fixed merchant. Remember it as VARIES.
    varies = len(counts) >= 3 and dominance < 0.75

    return {
        "entity_name": entity_name,
        "transaction_count": len(transactions),
        "category_counts": dict(counts),
        "dominant_category": None if varies else dominant_category,
        "dominance": round(dominance, 2),
        "memory_label": "VARIES" if varies else "STABLE",
    }


def should_create_personal_category(
    profile: dict[str, Any],
    *,
    minimum_transactions: int = 4,
    minimum_dominance: float = 0.70,
) -> bool:
    """Return whether history is strong enough to suggest a personalized category.

    This deliberately does not create a category merely because a person's name
    appears repeatedly. A stable purpose must be demonstrated by history.
    """
    if profile.get("memory_label") != "STABLE":
        return False
    if profile.get("transaction_count", 0) < minimum_transactions:
        return False
    return float(profile.get("dominance", 0.0)) >= minimum_dominance
