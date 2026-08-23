"""Evidence scoring for transaction-intelligence decisions.

This module deliberately separates evidence collection from the final decision.
A signal can support a category without being strong enough to justify an
automatic categorization.
"""

from __future__ import annotations

from typing import Any

from .context import history_categories
from .semantic import semantic_note_evidence


def _amount_signal(amount: float | int | None, history: list[dict[str, Any]], category: str) -> float:
    """Return a small, explainable signal when amount resembles this category's history.

    Repeated amounts are stronger than a single coincidence. Exact or near-exact
    matches contribute progressively, but the total signal is capped so amount
    alone cannot become an unconditional categorization rule.
    """
    if amount is None:
        return 0.0
    current = float(amount)
    if current <= 0:
        return 0.0

    ratios: list[float] = []
    for item in history:
        if item.get("category") != category or item.get("amount") is None:
            continue
        value = float(item["amount"])
        if value <= 0:
            continue
        ratios.append(abs(current - value) / max(current, value, 1.0))

    if not ratios:
        return 0.0

    exact_or_close = sum(ratio <= 0.10 for ratio in ratios)
    moderate_matches = sum(ratio <= 0.25 for ratio in ratios)

    if exact_or_close:
        # One close match is useful; repeated close matches strengthen the
        # signal, but the cap keeps this evidence deliberately secondary.
        return min(0.25, 0.10 + 0.05 * exact_or_close)
    if moderate_matches:
        return 0.05
    return 0.0


def collect_evidence(*, amount: float | int | None, note: str | None, payment_method: str | None, history: list[dict[str, Any]]) -> dict[str, Any]:
    """Collect independent evidence without making the final decision."""
    note_signal = semantic_note_evidence(note)
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
        add(str(note_category), 0.70 * note_confidence, "semantic transaction note")

    total_history = sum(history_counts.values())
    if total_history:
        for category, count in history_counts.items():
            share = count / total_history
            add(category, min(0.45, share * 0.45), f"merchant history ({count}/{total_history})")
            amount_signal = _amount_signal(amount, history, category)
            add(category, amount_signal, "repeated/similar historical amount")

    # Payment method is intentionally weak: UPI alone does not reveal purpose.
    if payment_method and str(payment_method).strip().lower() == "upi":
        for category in candidates:
            add(category, 0.0, "upi payment")

    ranked = sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    return {
        "ranked": ranked,
        "reasons": reasons,
        "note_category": note_category,
        "note_confidence": note_confidence,
        "semantic_candidates": note_signal.get("candidates", []),
        "semantic_reason": note_signal.get("reason", ""),
    }
