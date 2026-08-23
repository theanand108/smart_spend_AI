"""Context-aware transaction categorization for Smart Spend AI V2."""

from __future__ import annotations

from typing import Any

from .context import history_categories, history_profile, normalize_text
from .entity_memory import build_entity_profile, should_create_personal_category
from .evidence import collect_evidence

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


def _result(*, category: str | None, confidence: float, status: str, reason: str, needs_user_confirmation: bool, **extra: Any) -> dict[str, Any]:
    result = {"category": category, "confidence": round(max(0.0, min(1.0, confidence)), 2), "status": status, "reason": reason, "needs_user_confirmation": needs_user_confirmation}
    result.update(extra)
    return result


def categorize_transaction(merchant_name: str, amount: float | int | None = None, note: str | None = None, payment_method: str | None = None, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Categorize a transaction using independent evidence sources."""
    merchant = normalize_text(merchant_name)
    if not merchant:
        return _result(category=None, confidence=0.0, status="unknown", reason="Merchant name is missing.", needs_user_confirmation=True)

    known_category = _known_merchant_category(merchant)
    if known_category:
        return _result(category=known_category, confidence=0.99, status="categorized", reason="Merchant matches a known transaction category.", needs_user_confirmation=False)

    merchant_history = _history_for_merchant(merchant, history)
    historical_counts = history_categories(merchant_history)
    profile = history_profile(merchant_history)
    entity_profile = build_entity_profile(merchant, merchant_history)
    evidence = collect_evidence(amount=amount, note=note, payment_method=payment_method, history=merchant_history)

    note_category = evidence.get("note_category")
    note_confidence = float(evidence.get("note_confidence") or 0.0)

    if note_category and note_confidence >= 0.90:
        category = str(note_category)
        if historical_counts and category not in historical_counts:
            return _result(category=category, confidence=0.82, status="conflict", reason="Current transaction context is strong but conflicts with this entity's history.", needs_user_confirmation=True, entity_memory=entity_profile)
        return _result(category=category, confidence=note_confidence, status="categorized", reason="Current transaction note provides strong semantic evidence.", needs_user_confirmation=False, entity_memory=entity_profile)

    if profile["varies"] and not note_category:
        return _result(category=None, confidence=0.25, status="varies", reason="Entity history spans multiple categories, so this entity is remembered as VARIES.", needs_user_confirmation=True, entity_memory=entity_profile)

    personal_category_candidate = None
    if should_create_personal_category(entity_profile):
        personal_category_candidate = entity_profile["dominant_category"]

    if len(historical_counts) >= 2:
        ranked_history = sorted(historical_counts.values(), reverse=True)
        if ranked_history[0] == ranked_history[1]:
            return _result(category=None, confidence=0.20, status="conflict", reason="Entity has equally represented historical categories.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    ranked = evidence.get("ranked") or []
    if not ranked:
        return _result(category=None, confidence=0.05, status="unknown", reason="Available evidence does not provide enough context to categorize safely.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    top_category, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = top_score - second_score

    if note_category:
        return _result(category=str(note_category), confidence=min(0.89, max(0.35, top_score)), status="needs_confirmation", reason="The note provides useful but insufficiently strong evidence for silent categorization.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    if historical_counts and not profile["varies"] and profile["dominance"] >= 0.80 and margin >= 0.20:
        confidence = min(0.90, 0.65 + top_score * 0.30 + margin * 0.10)
        return _result(category=str(top_category), confidence=confidence, status="categorized", reason="Consistent entity history is reinforced by the available transaction evidence.", needs_user_confirmation=False, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    if top_score >= 0.35 and margin >= 0.12:
        confidence = min(0.84, 0.45 + top_score * 0.25 + margin * 0.10)
        return _result(category=str(top_category), confidence=confidence, status="needs_confirmation", reason="There is a leading category, but the evidence margin is not strong enough for silent categorization.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    return _result(category=None, confidence=min(0.40, top_score), status="unknown", reason="Evidence is too weak or conflicting to choose a category safely.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)
