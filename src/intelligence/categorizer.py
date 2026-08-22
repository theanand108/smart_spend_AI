"""Context-aware transaction categorization for Smart Spend AI V2."""

from __future__ import annotations

from typing import Any

from .context import history_categories, history_profile, note_evidence, normalize_text

KNOWN_MERCHANTS: dict[str, str] = {
    "zomato": "Food & Dining", "swiggy": "Food & Dining", "starbucks": "Food & Dining",
    "dominoz": "Food & Dining", "uber": "Travel & Transport", "ola": "Travel & Transport",
    "petrol": "Travel & Transport", "netflix": "Entertainment", "spotify": "Entertainment",
    "bookmyshow": "Entertainment", "blinkit": "Groceries", "kirana": "Groceries",
    "airtel": "Bills & Utilities", "myntra": "Shopping", "h&m": "Shopping",
    "amazon": "Shopping", "flipkart": "Shopping", "gym": "Health & Fitness",
    "health": "Health & Fitness", "hospital": "Health & Fitness",
}


def _known_merchant_category(merchant_name: str) -> str | None:
    for merchant, category in KNOWN_MERCHANTS.items():
        if merchant in merchant_name:
            return category
    return None


def _history_for_merchant(merchant_name: str, history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized = normalize_text(merchant_name)
    return [item for item in (history or []) if normalize_text(item.get("merchant_name")) == normalized]


def _amount_similarity(amount: float | int | None, values: list[float]) -> float:
    """Return a small similarity signal for repeated transaction amounts."""
    if amount is None or not values:
        return 0.0
    current = float(amount)
    if current <= 0:
        return 0.0
    closest_ratio = min(abs(current - value) / max(current, value, 1.0) for value in values)
    if closest_ratio <= 0.10:
        return 1.0
    if closest_ratio <= 0.25:
        return 0.5
    return 0.0


def _result(*, category: str | None, confidence: float, status: str, reason: str, needs_user_confirmation: bool) -> dict[str, Any]:
    return {
        "category": category,
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
        "status": status,
        "reason": reason,
        "needs_user_confirmation": needs_user_confirmation,
    }


def categorize_transaction(
    merchant_name: str,
    amount: float | int | None = None,
    note: str | None = None,
    payment_method: str | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Categorize one transaction while explicitly representing uncertainty.

    The decision order is deliberately evidence-first:
    known merchant -> explicit note -> merchant memory -> unknown.
    History is a prior, never proof. A merchant used for several purposes is
    treated as VARIES and should not be silently forced into one category.
    Amount similarity is only a supporting signal; it cannot rescue an
    otherwise ambiguous transaction by itself.
    """
    del payment_method  # Reserved for the future feature-scoring/ML layer.
    merchant = normalize_text(merchant_name)
    if not merchant:
        return _result(category=None, confidence=0.0, status="unknown", reason="Merchant name is missing.", needs_user_confirmation=True)

    known_category = _known_merchant_category(merchant)
    if known_category:
        return _result(category=known_category, confidence=0.99, status="categorized", reason="Merchant matches a known transaction category.", needs_user_confirmation=False)

    evidence = note_evidence(note)
    merchant_history = _history_for_merchant(merchant, history)
    historical_counts = history_categories(merchant_history)
    profile = history_profile(merchant_history)
    evidence_category = evidence.get("category")
    evidence_confidence = float(evidence.get("confidence") or 0.0)

    if evidence_category:
        note_category = str(evidence_category)
        if historical_counts and note_category not in historical_counts:
            return _result(category=note_category, confidence=0.78, status="conflict", reason="Current note conflicts with this merchant's historical category.", needs_user_confirmation=True)
        if evidence_confidence >= 0.90:
            return _result(category=note_category, confidence=evidence_confidence, status="categorized", reason=str(evidence.get("reason")), needs_user_confirmation=False)
        return _result(category=note_category, confidence=evidence_confidence, status="needs_confirmation", reason="The note provides a plausible category but not enough evidence for automatic categorization.", needs_user_confirmation=True)

    if historical_counts:
        if profile["varies"]:
            return _result(category=None, confidence=0.25, status="varies", reason="Merchant history spans multiple categories, so this merchant is remembered as VARIES.", needs_user_confirmation=True)

        ranked = sorted(historical_counts.items(), key=lambda item: item[1], reverse=True)
        top_category, top_count = ranked[0]
        second_count = ranked[1][1] if len(ranked) > 1 else 0
        if top_count == second_count:
            return _result(category=None, confidence=0.2, status="conflict", reason="Merchant has conflicting historical categories.", needs_user_confirmation=True)

        # Amount similarity can strengthen a dominant memory, but cannot create
        # a category when history itself is mixed or absent.
        category_amounts = [
            float(item["amount"])
            for item in merchant_history
            if item.get("category") == top_category and item.get("amount") is not None
        ]
        amount_signal = _amount_similarity(amount, category_amounts)
        confidence = 0.72 + (0.08 if amount_signal else 0.0)
        if profile["dominance"] < 0.80:
            return _result(category=top_category, confidence=confidence, status="needs_confirmation", reason="History has a dominant category but is not consistent enough for silent categorization.", needs_user_confirmation=True)
        return _result(category=top_category, confidence=min(0.9, confidence), status="categorized", reason="Merchant matches a consistent historical category; amount similarity is supporting evidence." if amount_signal else "Merchant matches a consistent historical category in transaction history.", needs_user_confirmation=False)

    return _result(category=None, confidence=0.05, status="unknown", reason="Merchant identity does not provide enough context to categorize safely.", needs_user_confirmation=True)
