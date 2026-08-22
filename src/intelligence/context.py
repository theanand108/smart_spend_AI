"""Context extraction helpers used by transaction intelligence."""

from __future__ import annotations

import re
from typing import Any


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Food & Dining": (
        "food", "dinner", "lunch", "breakfast", "tea", "chai", "coffee",
        "snack", "bakery", "cake", "restaurant", "canteen", "dining",
    ),
    "Health & Fitness": (
        "medicine", "medicines", "pharmacy", "tablet", "tablets", "doctor",
        "hospital", "healthcare", "health", "fever", "gym",
    ),
    "Transfer / Personal": (
        "borrowed", "borrow", "loan", "owed", "paid back", "repayment",
        "refund", "reimbursement", "allowance", "sent for", "family transfer",
        "personal", "split dinner",
    ),
    "Housing / Rent": ("rent", "room rent", "landlord", "monthly room"),
    "Education": (
        "college", "semester", "semester fee", "semester fees", "fee", "fees",
        "notebooks", "pens", "stationery", "education",
    ),
    "Travel & Transport": (
        "ride", "auto", "rickshaw", "transport", "petrol", "fuel", "uber", "ola",
    ),
    "Groceries": (
        "grocery", "groceries", "kirana", "vegetables", "vegetable", "milk",
        "ration", "grocery purchase",
    ),
    "Shopping": (
        "clothing", "clothes", "kurti", "shopping", "purchase", "extension board",
        "hardware", "household",
    ),
    "Bills & Utilities": (
        "recharge", "mobile recharge", "phone recharge", "electricity", "water bill",
        "mobile bill", "internet", "bill", "airtel",
    ),
    "Entertainment": ("movie", "streaming", "netflix", "spotify", "entertainment"),
}

# Notes such as "ok", "home", "personal", "payment", or "stuff" are too weak
# to justify a confident category by themselves.
WEAK_NOTE_WORDS = {
    "ok", "home", "personal", "payment", "stuff", "monthly", "urgent", "for", "the",
}

# More specific phrases should outweigh incidental context words. For example,
# "tea from college shop" contains both "tea" and "college", but the purchase
# is clearly food-related rather than an education expense.
STRONG_PHRASES: dict[str, tuple[str, ...]] = {
    "Food & Dining": (
        "tea from", "chai from", "coffee from", "food from", "lunch from",
        "dinner from", "breakfast from", "college canteen", "college cafeteria",
    ),
    "Health & Fitness": (
        "medicine for", "medicines for", "tablet for", "doctor visit", "pharmacy purchase",
    ),
    "Housing / Rent": ("monthly room rent", "room rent", "monthly rent"),
    "Travel & Transport": ("auto ride", "cab ride", "uber ride", "ola ride"),
    "Groceries": ("grocery purchase", "grocery shopping", "monthly groceries"),
    "Bills & Utilities": ("mobile recharge", "phone recharge", "electricity bill", "water bill"),
}


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.strip().lower())


def note_evidence(note: Any) -> dict[str, str | float | None]:
    text = normalize_text(note)
    if not text:
        return {"category": None, "confidence": 0.0, "reason": "No transaction note provided."}

    tokens = set(re.findall(r"[a-z]+", text))
    meaningful_tokens = tokens - WEAK_NOTE_WORDS
    if not meaningful_tokens:
        return {"category": None, "confidence": 0.0, "reason": "Note is too weak to identify the transaction."}

    # Specific phrases are the strongest deterministic evidence.
    phrase_matches: list[tuple[str, str]] = []
    for category, phrases in STRONG_PHRASES.items():
        for phrase in phrases:
            if phrase in text:
                phrase_matches.append((category, phrase))

    if phrase_matches:
        categories = {category for category, _ in phrase_matches}
        if len(categories) == 1:
            category, phrase = phrase_matches[0]
            return {
                "category": category,
                "confidence": 0.95,
                "reason": f'Note contains the specific phrase "{phrase}".',
            }
        return {"category": None, "confidence": 0.0, "reason": "Note contains conflicting category clues."}

    matches: list[tuple[str, int, str]] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        matched = [keyword for keyword in keywords if keyword in text]
        if matched:
            matches.append((category, len(matched), matched[0]))

    if not matches:
        return {"category": None, "confidence": 0.0, "reason": "Note does not contain enough category evidence."}

    matches.sort(key=lambda item: item[1], reverse=True)
    category, _, keyword = matches[0]
    if len(matches) > 1 and matches[0][1] == matches[1][1]:
        return {"category": None, "confidence": 0.0, "reason": "Note contains conflicting category clues."}

    # Explicit semantic phrases are stronger than a single generic keyword.
    confidence = 0.92 if len(meaningful_tokens) >= 2 else 0.82
    return {
        "category": category,
        "confidence": confidence,
        "reason": f'Note contains "{keyword}" as category evidence.',
    }


def history_categories(history: list[dict[str, Any]] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in history or []:
        category = item.get("category")
        if category and category != "Others":
            counts[category] = counts.get(category, 0) + 1
    return counts
