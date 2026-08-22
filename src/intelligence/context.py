"""Context extraction helpers used by transaction intelligence V2."""

from __future__ import annotations

import re
from typing import Any

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Food & Dining": ("food", "dinner", "lunch", "breakfast", "tea", "chai", "coffee", "snack", "bakery", "cake", "restaurant", "canteen", "dining"),
    "Health & Fitness": ("medicine", "medicines", "pharmacy", "tablet", "tablets", "doctor", "hospital", "healthcare", "health", "fever", "gym"),
    "Transfer / Personal": ("borrowed", "borrow", "loan", "owed", "paid back", "repayment", "refund", "reimbursement", "allowance", "sent for", "family transfer", "personal", "split dinner", "split bill", "my share", "friend's share"),
    "Housing / Rent": ("rent", "room rent", "landlord", "monthly room"),
    "Education": ("college", "semester", "semester fee", "semester fees", "fee", "fees", "notebooks", "pens", "stationery", "education"),
    "Travel & Transport": ("ride", "auto", "rickshaw", "transport", "petrol", "fuel", "uber", "ola"),
    "Groceries": ("grocery", "groceries", "kirana", "vegetables", "vegetable", "milk", "ration", "grocery purchase"),
    "Shopping": ("clothing", "clothes", "kurti", "shopping", "purchase", "extension board", "hardware", "household", "plumbing"),
    "Bills & Utilities": ("recharge", "mobile recharge", "phone recharge", "electricity", "water bill", "mobile bill", "internet", "bill", "airtel"),
    "Entertainment": ("movie", "streaming", "netflix", "spotify", "entertainment"),
}

WEAK_NOTE_WORDS = {"ok", "home", "personal", "payment", "stuff", "monthly", "urgent", "for", "the", "gift"}

STRONG_PHRASES: dict[str, tuple[str, ...]] = {
    "Food & Dining": ("tea from", "chai from", "coffee from", "food from", "lunch from", "dinner from", "breakfast from", "college canteen", "college cafeteria", "friend paid the bill", "my share of dinner", "my share of the dinner", "split dinner", "split the dinner", "split the bill", "my share of the bill"),
    "Health & Fitness": ("medicine for", "medicines for", "tablet for", "doctor visit", "pharmacy purchase", "medicine from", "medicines from"),
    "Housing / Rent": ("monthly room rent", "room rent", "monthly rent"),
    "Travel & Transport": ("auto ride", "cab ride", "uber ride", "ola ride", "ride to college", "friend bought my ticket"),
    "Groceries": ("grocery purchase", "grocery shopping", "monthly groceries", "vegetables for us", "vegetables for me", "groceries for us", "groceries for me", "milk for us", "ration for us"),
    "Bills & Utilities": ("mobile recharge", "phone recharge", "electricity bill", "water bill"),
    "Transfer / Personal": ("sent back what i borrowed", "paying back my friend", "paid back my friend", "returning borrowed money", "returning what i borrowed", "money i owed", "sent money to friend", "transferred to friend", "transfer to friend"),
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
    phrase_matches: list[tuple[str, str]] = []
    for category, phrases in STRONG_PHRASES.items():
        for phrase in phrases:
            if phrase in text:
                phrase_matches.append((category, phrase))
    if phrase_matches:
        categories = {category for category, _ in phrase_matches}
        if len(categories) == 1:
            category, phrase = phrase_matches[0]
            return {"category": category, "confidence": 0.95, "reason": f'Note contains the specific phrase "{phrase}".'}
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
    confidence = 0.82 if len(meaningful_tokens) <= 2 else 0.86
    return {"category": category, "confidence": confidence, "reason": f'Note contains "{keyword}" as category evidence.'}


def history_categories(history: list[dict[str, Any]] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in history or []:
        category = item.get("category")
        if category and category not in {"Others", "Unknown", "VARIES"}:
            counts[category] = counts.get(category, 0) + 1
    return counts


def history_profile(history: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Summarize merchant memory without pretending one category is always true."""
    counts = history_categories(history)
    total = sum(counts.values())
    if not counts:
        return {"counts": {}, "total": 0, "dominant_category": None, "dominance": 0.0, "varies": False}
    dominant_category, dominant_count = max(counts.items(), key=lambda item: item[1])
    dominance = dominant_count / total
    # Reserve VARIES for merchants with several genuinely different uses.
    varies = len(counts) >= 3 and dominance < 0.75
    return {
        "counts": counts,
        "total": total,
        "dominant_category": dominant_category,
        "dominance": dominance,
        "varies": varies,
    }
