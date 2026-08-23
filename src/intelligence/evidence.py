"""Evidence scoring for transaction-intelligence decisions.

This module deliberately separates evidence collection from the final decision.
A signal can support a category without being strong enough to justify an
automatic categorization.
"""

from __future__ import annotations

from typing import Any

from .context import history_categories, note_evidence


def _amount_signal(
    amount: float | int | None,
    history: list[dict[str, Any]],
    category: str,
) -> float:
    """Return a small signal when the current amount resembles this category's history."""
    if amount is None:
        return 0.0
    current = float(amount)
    if current <= 0:
        return 0.0
    values = [
        float(item["amount"])
        for item in history
        if item.get("category") == category and item.get("amount") is not None
    ]
    if not values:
        return 0.0
    closest_ratio = min(abs(current - value) / max(current, value, 1.0) for value in values)
    if closest_ratio <= 0.10:
        return 0.15
    if closest_ratio <= 0.25:
        return 0.07
    return 0.0


def collect_evidence(
    *,
    amount: float | int | None,
    note: str | None,
    payment_method: str | None,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Collect independent evidence without making the final decision."""
    note_signal = note_evidence(note)
    history_counts = history_categories(history)

    candidates: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}

    def add(category: str, score: float, reason: str) -> None:
        if score <= 0:
            return
        candidates[category] = candidates.get(category, 0.0) + score
        reasons.setdefault(category, []).append(reason)

    note_category = note_signal.get("category")
    note_confidence = float(note_signal.get("confidence") or 0.0)
    if note_category:
        # Explicit semantic context is the strongest non-merchant signal.
        add(str(note_category), 0.70 * note_confidence, "current transaction note")

    total_history = sum(history_counts.values())
    if total_history:
        for category, count in history_counts.items():
            share = count / total_history
            add(category, min(0.45, share * 0.45), f"merchant history ({count}/{total_history})")
            amount_score = _amount_signal(amount, history, category)
            add(category, amount_score, "similar historical amount")

    # Payment method is intentionally a weak feature for now. UPI itself does
    # not tell us what the purchase was; it becomes useful only in combination
    # with stronger contextual features or future learned patterns.
    if payment_method:
        method = str(payment_method).strip().lower()
        if method in {"upi", "upi qr", "upi"}:
            for category in candidates:
                add(category, 0.0, "upi payment")

    ranked = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    return {
        "ranked": ranked,
        "reasons": reasons,
        "note_category": note_category,
        "note_confidence": note_confidence,
    }
