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

    merchant_history = _history_for_merchant(merchant, history)
    historical_counts = history_categories(merchant_history)
    profile = history_profile(merchant_history)
    entity_profile = build_entity_profile(merchant, merchant_history)
    evidence = collect_evidence(amount=amount, note=note, merchant_name=merchant, payment_method=payment_method, history=merchant_history)

    known_category = _known_merchant_category(merchant)
    if known_category:
        evidence["known_merchant_category"] = known_category
        evidence["known_merchant_confidence"] = 0.99
        evidence.setdefault("reasons", {}).setdefault(known_category, []).append("known merchant mapping")
        evidence.setdefault("ranked", []).append((known_category, 0.99))
        evidence["ranked"] = sorted(evidence["ranked"], key=lambda item: item[1], reverse=True)

    note_category = evidence.get("note_category")
    note_confidence = float(evidence.get("note_confidence") or 0.0)
    merchant_category = evidence.get("merchant_category")
    merchant_confidence = float(evidence.get("merchant_confidence") or 0.0)

    # A strong current note is the user's explicit description of this specific
    # transaction. It outranks entity history: a person/merchant can be used
    # for many purposes, while the note explains what happened this time.
    if note_category and note_confidence >= 0.90:
        return _result(category=str(note_category), confidence=note_confidence, status="categorized", reason="Current transaction note provides strong semantic evidence and takes precedence over historical entity behavior.", needs_user_confirmation=False, entity_memory=entity_profile)

    if known_category:
        return _result(category=known_category, confidence=0.99, status="categorized", reason="Merchant matches a known high-confidence transaction category.", needs_user_confirmation=False, entity_memory=entity_profile)

    if normalize_text(note) and not note_category:
        if merchant_category:
            return _result(category=str(merchant_category), confidence=min(0.84, max(0.35, merchant_confidence)), status="needs_confirmation", reason="The note is vague, so merchant semantic evidence is used as supporting context rather than silently reusing history.", needs_user_confirmation=True, entity_memory=entity_profile)
        return _result(category=None, confidence=0.05, status="unknown", reason="The note is too vague to identify transaction purpose; historical category memory is not strong enough to override it silently.", needs_user_confirmation=True, entity_memory=entity_profile)

    personal_category_candidate = None
    if should_create_personal_category(entity_profile):
        personal_category_candidate = entity_profile["dominant_category"]

    ranked = evidence.get("ranked") or []
    amount_matches = evidence.get("amount_matches") or {}
    historical_semantic_matches = evidence.get("historical_semantic_matches") or {}

    if not note_category and ranked:
        for category, semantic_count in historical_semantic_matches.items():
            if semantic_count >= 2 and int(amount_matches.get(category, 0)) >= 1:
                return _result(category=str(category), confidence=0.78, status="needs_confirmation", reason="Repeated historical notes and a matching amount support this category, but the entity has mixed or incomplete history.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    if profile["varies"] and not note_category:
        return _result(category=None, confidence=0.25, status="varies", reason="Entity history spans multiple categories, so this entity is remembered as VARIES.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    if not ranked:
        return _result(category=None, confidence=0.05, status="unknown", reason="Available evidence does not provide enough context to categorize safely.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    top_category, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = top_score - second_score

    if merchant_category and top_category == merchant_category and merchant_confidence >= 0.90:
        return _result(category=str(merchant_category), confidence=min(0.90, max(0.50, merchant_confidence)), status="categorized", reason="Merchant language provides strong, unambiguous semantic evidence for this transaction.", needs_user_confirmation=False, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    if note_category:
        return _result(category=str(note_category), confidence=min(0.89, max(0.35, note_confidence)), status="needs_confirmation", reason="The note provides useful but insufficiently strong evidence for silent categorization.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    if len(historical_counts) == 1 and int(amount_matches.get(str(top_category), 0)) >= 1:
        close_matches = int(amount_matches[str(top_category)])
        confidence = min(0.84, 0.68 + 0.04 * close_matches)
        return _result(category=str(top_category), confidence=confidence, status="categorized", reason="The entity has one historical purpose and the current amount closely matches a previous transaction.", needs_user_confirmation=False, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    if len(historical_counts) >= 2:
        ranked_history = sorted(historical_counts.values(), reverse=True)
        top_amount_matches = int(amount_matches.get(str(top_category), 0))
        competing_amount_matches = max((int(amount_matches.get(str(category), 0)) for category in historical_counts if category != top_category), default=0)
        if top_amount_matches >= 2 and top_amount_matches > competing_amount_matches:
            confidence = min(0.88, 0.70 + 0.04 * top_amount_matches + max(0.0, margin) * 0.10)
            return _result(category=str(top_category), confidence=confidence, status="categorized", reason="Repeated historical amounts consistently support this category despite mixed entity history.", needs_user_confirmation=False, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

        if ranked_history[0] == ranked_history[1] and margin < 0.12:
            return _result(category=None, confidence=0.20, status="conflict", reason="Entity has equally represented historical categories and the current amount does not provide enough separation.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    if historical_counts and not profile["varies"] and profile["dominance"] >= 0.80:
        if entity_profile.get("transaction_count", 0) >= 4 and margin >= 0.20:
            confidence = min(0.90, 0.65 + top_score * 0.30 + margin * 0.10)
            return _result(category=str(top_category), confidence=confidence, status="categorized", reason="Consistent entity history across several transactions is reinforced by the available evidence.", needs_user_confirmation=False, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

        return _result(category=None, confidence=min(0.35, top_score), status="unknown", reason="Historical evidence is too small to silently reuse without a matching amount or current note.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    if top_score >= 0.35 and margin >= 0.12:
        confidence = min(0.84, 0.45 + top_score * 0.25 + margin * 0.10)
        return _result(category=str(top_category), confidence=confidence, status="needs_confirmation", reason="There is a leading category, but the evidence margin is not strong enough for silent categorization.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)

    return _result(category=None, confidence=min(0.40, top_score), status="unknown", reason="Evidence is too weak or conflicting to choose a category safely.", needs_user_confirmation=True, entity_memory=entity_profile, personal_category_candidate=personal_category_candidate)
