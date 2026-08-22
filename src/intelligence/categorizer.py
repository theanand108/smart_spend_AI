"""Context-aware transaction categorization for Smart Spend AI V2."""

from __future__ import annotations

from typing import Any

from .context import history_categories, note_evidence, normalize_text

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
    """Categorize one transaction and explicitly represent uncertainty.

    Strong transaction-specific context can auto-categorize. Weaker context is
    surfaced to the user for confirmation instead of becoming false confidence.
    History is a prior, not proof, because a friend can receive payments for
    groceries, medicine, shared meals, or personal transfers on different days.
    """
    del amount, payment_method
    merchant = normalize_text(merchant_name)
    if not merchant:
        return _result(category=None, confidence=0.0, status="unknown", reason="Merchant name is missing.", needs_user_confirmation=True)

    known_category = _known_merchant_category(merchant)
    if known_category:
        return _result(category=known_category, confidence=0.99, status="categorized", reason="Merchant matches a known transaction category.", needs_user_confirmation=False)

    evidence = note_evidence(note)
    merchant_history = _history_for_merchant(merchant, history)
    historical_counts = history_categories(merchant_history)
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
        ranked = sorted(historical_counts.items(), key=lambda item: item[1], reverse=True)
        top_category, top_count = ranked[0]
        second_count = ranked[1][1] if len(ranked) > 1 else 0
        if top_count == second_count:
            return _result(category=None, confidence=0.2, status="conflict", reason="Merchant has conflicting historical categories.", needs_user_confirmation=True)
        confidence = 0.72 if top_count == 1 else min(0.9, 0.72 + 0.05 * (top_count - 1))
        return _result(category=top_category, confidence=confidence, status="categorized", reason="Merchant matches a previously confirmed category in transaction history.", needs_user_confirmation=False)

    return _result(category=None, confidence=0.05, status="unknown", reason="Merchant identity does not provide enough context to categorize safely.", needs_user_confirmation=True)
