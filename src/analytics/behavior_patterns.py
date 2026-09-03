"""Behavioral pattern detection over deterministic financial facts.

This layer identifies *how* spending changed without generating user-facing copy
or recalculating transaction metrics. It returns structured evidence for the
insight engine to reason over.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal

from src.analytics.financial_facts import FinancialFacts


MIN_NEW_CATEGORY_AMOUNT = Decimal("500")
MIN_MERCHANT_DRIVER_SHARE = Decimal("0.40")
SMALL_AVERAGE_CHANGE_RATIO = Decimal("0.10")
SMALL_AVERAGE_CHANGE_AMOUNT = Decimal("500")


@dataclass(frozen=True)
class BehaviorPattern:
    """A detected behavioral pattern backed by financial facts."""

    pattern_type: str
    confidence: Decimal
    category: str | None
    merchant: str | None
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _average_is_stable(facts: FinancialFacts) -> bool:
    change = abs(facts.average_transaction_change)
    if change == 0:
        return True
    if change <= SMALL_AVERAGE_CHANGE_AMOUNT:
        return True
    if facts.previous_average_transaction == 0:
        return False
    return (
        change / facts.previous_average_transaction
    ) <= SMALL_AVERAGE_CHANGE_RATIO


def _meaningful_average_increase(facts: FinancialFacts) -> bool:
    change = facts.average_transaction_change
    if change <= 0:
        return False
    if change >= SMALL_AVERAGE_CHANGE_AMOUNT:
        return True
    if facts.previous_average_transaction == 0:
        return True
    return change / facts.previous_average_transaction >= SMALL_AVERAGE_CHANGE_RATIO


def _new_category_pattern(facts: FinancialFacts) -> BehaviorPattern | None:
    new_categories = [
        item
        for item in facts.category_changes
        if item.previous_amount == 0 and item.current_amount >= MIN_NEW_CATEGORY_AMOUNT
    ]
    if not new_categories:
        return None

    item = max(new_categories, key=lambda change: change.current_amount)
    return BehaviorPattern(
        pattern_type="new_spending_area",
        confidence=Decimal("0.90"),
        category=item.category,
        merchant=None,
        evidence=(
            f"{item.category} had no spending in the previous period.",
            f"Current spending in {item.category} is {item.current_amount}.",
        ),
    )


def _merchant_pattern(facts: FinancialFacts) -> BehaviorPattern | None:
    if facts.spending_change <= 0:
        return None
    if facts.spending_change == 0:
        return None

    positive = [item for item in facts.merchant_changes if item.amount_change > 0]
    if not positive:
        return None

    item = max(positive, key=lambda change: change.amount_change)
    share = item.amount_change / facts.spending_change
    if share < MIN_MERCHANT_DRIVER_SHARE:
        return None

    return BehaviorPattern(
        pattern_type="merchant_driven_increase",
        confidence=min(Decimal("1"), Decimal("0.60") + share),
        category=None,
        merchant=item.merchant,
        evidence=(
            f"{item.merchant} increased by {item.amount_change}.",
            f"The merchant accounts for {share * Decimal('100'):.0f}% of the net spending change.",
        ),
    )


def _frequency_pattern(facts: FinancialFacts) -> BehaviorPattern | None:
    if facts.spending_change <= 0:
        return None
    if facts.previous_transaction_count == 0:
        return None
    if facts.transaction_count_change < 2:
        return None
    if not _average_is_stable(facts):
        return None

    confidence = Decimal("0.80")
    if facts.transaction_count_change >= 4:
        confidence += Decimal("0.10")

    return BehaviorPattern(
        pattern_type="frequency_driven_increase",
        confidence=min(confidence, Decimal("1")),
        category=None,
        merchant=None,
        evidence=(
            f"Transaction count increased by {facts.transaction_count_change}.",
            f"Average transaction changed by {facts.average_transaction_change}.",
        ),
    )


def _basket_size_pattern(facts: FinancialFacts) -> BehaviorPattern | None:
    if facts.spending_change <= 0:
        return None
    if facts.transaction_count_change > 0:
        return None
    if not _meaningful_average_increase(facts):
        return None

    return BehaviorPattern(
        pattern_type="basket_size_driven_increase",
        confidence=Decimal("0.85"),
        category=None,
        merchant=None,
        evidence=(
            f"Average transaction increased by {facts.average_transaction_change}.",
            f"Transaction count changed by {facts.transaction_count_change}.",
        ),
    )


def _distributed_pattern(facts: FinancialFacts) -> BehaviorPattern | None:
    if facts.spending_change <= 0:
        return None

    positive_categories = [
        item for item in facts.category_changes if item.amount_change > 0
    ]
    if not positive_categories:
        return None

    largest = max(positive_categories, key=lambda item: item.amount_change)
    share = largest.amount_change / facts.spending_change
    if share >= Decimal("0.40"):
        return None

    return BehaviorPattern(
        pattern_type="distributed_increase",
        confidence=Decimal("0.80"),
        category=None,
        merchant=None,
        evidence=(
            f"The largest category accounts for {share * Decimal('100'):.0f}% of the net spending change.",
            f"{len(positive_categories)} categories increased spending.",
        ),
    )


def detect_behavior_patterns(facts: FinancialFacts) -> list[dict[str, object]]:
    """Detect a small, explainable set of behavioral patterns."""

    candidates = [
        _frequency_pattern(facts),
        _basket_size_pattern(facts),
        _new_category_pattern(facts),
        _merchant_pattern(facts),
        _distributed_pattern(facts),
    ]
    patterns = [pattern for pattern in candidates if pattern is not None]
    patterns.sort(key=lambda pattern: pattern.confidence, reverse=True)
    return [pattern.to_dict() for pattern in patterns]
