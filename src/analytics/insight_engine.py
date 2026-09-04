"""Evidence-backed financial insight generation.

This module sits above ``financial_facts`` and ``behavior_patterns``. It
reasons over deterministic facts and explainable behavioral evidence without
recalculating financial metrics, touching the database, or generating
presentation copy. The output is structured so the dashboard (or a future AI
language layer) can decide how to present it.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal

from src.analytics.behavior_patterns import detect_behavior_patterns
from src.analytics.financial_facts import FinancialFacts


MEANINGFUL_CHANGE_RATIO = Decimal("0.10")
MEANINGFUL_CHANGE_AMOUNT = Decimal("500")
MIN_DRIVER_SHARE = Decimal("0.25")
MIN_FREQUENCY_CHANGE = 2
MIN_CATEGORY_SPIKE_AMOUNT = Decimal("500")
MIN_CATEGORY_SPIKE_RATIO = Decimal("0.25")


@dataclass(frozen=True)
class FinancialInsight:
    """A structured, evidence-backed financial insight."""

    insight_type: str
    severity: str
    title: str
    category: str | None
    merchant: str | None
    change_amount: Decimal
    change_percent: Decimal | None
    driver: str
    recommendation: str
    evidence: tuple[str, ...]
    priority: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _meaningful_change(change: Decimal, previous: Decimal) -> bool:
    if change == 0:
        return False
    if abs(change) >= MEANINGFUL_CHANGE_AMOUNT:
        return True
    if previous == 0:
        return True
    return abs(change / previous) >= MEANINGFUL_CHANGE_RATIO


def _category_driver(facts: FinancialFacts):
    if facts.spending_change == 0:
        return None

    candidates = [item for item in facts.category_changes if item.amount_change != 0]
    if not candidates:
        return None

    if facts.spending_change > 0:
        item = max(candidates, key=lambda change: change.amount_change)
        if item.amount_change <= 0:
            return None
    else:
        item = min(candidates, key=lambda change: change.amount_change)
        if item.amount_change >= 0:
            return None

    share = abs(item.amount_change / facts.spending_change)
    if share < MIN_DRIVER_SHARE:
        return None
    return item, share


def _merchant_driver(facts: FinancialFacts):
    if facts.spending_change == 0:
        return None

    candidates = [item for item in facts.merchant_changes if item.amount_change != 0]
    if not candidates:
        return None

    if facts.spending_change > 0:
        item = max(candidates, key=lambda change: change.amount_change)
        if item.amount_change <= 0:
            return None
    else:
        item = min(candidates, key=lambda change: change.amount_change)
        if item.amount_change >= 0:
            return None

    share = abs(item.amount_change / facts.spending_change)
    if share < MIN_DRIVER_SHARE:
        return None
    return item, share


def _build_change_insight(facts: FinancialFacts) -> FinancialInsight | None:
    change = facts.spending_change
    if not _meaningful_change(change, facts.previous_spending):
        return None

    category_driver = _category_driver(facts)
    merchant_driver = _merchant_driver(facts)

    if change > 0:
        severity = "attention"
        recommendation = "review_driver"
        title = "Spending increased"
        insight_type = "spending_increase"
        driver = "overall_increase"
        evidence = (f"Spending changed by {change} compared with the previous period.",)
        priority = 50
    else:
        severity = "positive"
        recommendation = "maintain_pattern"
        title = "Spending decreased"
        insight_type = "spending_decrease"
        driver = "overall_decrease"
        evidence = (f"Spending changed by {change} compared with the previous period.",)
        priority = 45

    category = None
    merchant = None
    change_amount = change

    if category_driver:
        item, share = category_driver
        category = item.category
        driver = "category_increase" if change > 0 else "category_reduction"
        change_amount = item.amount_change
        evidence = evidence + (
            f"{category} accounts for {share * Decimal('100'):.0f}% of the net change.",
        )
        if change > 0:
            recommendation = "review_category"
            priority += 5

    if merchant_driver:
        item, share = merchant_driver
        merchant = item.merchant
        evidence = evidence + (
            f"{merchant} accounts for {share * Decimal('100'):.0f}% of the net change.",
        )
        if category_driver:
            driver = "category_and_merchant"
        else:
            driver = "merchant_increase" if change > 0 else "merchant_reduction"
            change_amount = item.amount_change
            recommendation = "review_merchant" if change > 0 else "maintain_pattern"

    return FinancialInsight(
        insight_type=insight_type,
        severity=severity,
        title=title,
        category=category,
        merchant=merchant,
        change_amount=change_amount,
        change_percent=facts.spending_change_percent,
        driver=driver,
        recommendation=recommendation,
        evidence=evidence,
        priority=priority,
    )


def _build_category_spike_insight(facts: FinancialFacts) -> FinancialInsight | None:
    candidates = []
    for item in facts.category_changes:
        if item.amount_change < MIN_CATEGORY_SPIKE_AMOUNT:
            continue
        if item.previous_amount > 0 and item.amount_change / item.previous_amount < MIN_CATEGORY_SPIKE_RATIO:
            continue
        candidates.append(item)

    if not candidates:
        return None

    item = max(candidates, key=lambda change: change.amount_change)
    percent = item.change_percent
    return FinancialInsight(
        insight_type="category_spike",
        severity="attention",
        title="A spending area jumped",
        category=item.category,
        merchant=None,
        change_amount=item.amount_change,
        change_percent=percent,
        driver="category_spike",
        recommendation="review_category_spike",
        evidence=(
            f"{item.category} increased by {item.amount_change} compared with the previous period.",
            f"Current spending in {item.category} is {item.current_amount}.",
        ),
        priority=86,
    )


def _behavior_pattern(facts: FinancialFacts, pattern_type: str):
    return next(
        (pattern for pattern in detect_behavior_patterns(facts) if pattern["pattern_type"] == pattern_type),
        None,
    )


def _build_frequency_insight(facts: FinancialFacts) -> FinancialInsight | None:
    pattern = _behavior_pattern(facts, "frequency_change")
    if pattern is None:
        return None

    change = facts.transaction_count_change
    if change > 0:
        title = "You made more purchases"
        recommendation = "review_purchase_frequency"
    else:
        return None

    return FinancialInsight(
        insight_type="frequency_increase",
        severity="observation",
        title=title,
        category=None,
        merchant=None,
        change_amount=facts.spending_change,
        change_percent=facts.spending_change_percent,
        driver="frequency_increase",
        recommendation=recommendation,
        evidence=tuple(pattern["evidence"]),
        priority=82,
    )


def _build_average_transaction_insight(facts: FinancialFacts) -> FinancialInsight | None:
    if _behavior_pattern(facts, "basket_size_driven_increase") is not None:
        return None
    if facts.spending_change <= 0:
        return None
    if not _meaningful_change(
        facts.average_transaction_change, facts.previous_average_transaction
    ):
        return None
    if facts.transaction_count_change > 0:
        return None

    return FinancialInsight(
        insight_type="average_transaction_increase",
        severity="observation",
        title="Your typical transaction got larger",
        category=None,
        merchant=None,
        change_amount=facts.average_transaction_change,
        change_percent=facts.average_transaction_change_percent,
        driver="average_transaction_increase",
        recommendation="review_large_purchases",
        evidence=(
            f"Average transaction changed by {facts.average_transaction_change}.",
            f"Transaction count changed by {facts.transaction_count_change}.",
        ),
        priority=72,
    )


def _build_behavior_insights(facts: FinancialFacts) -> list[FinancialInsight]:
    insights: list[FinancialInsight] = []

    basket = _behavior_pattern(facts, "basket_size_driven_increase")
    if basket is not None:
        insights.append(
            FinancialInsight(
                insight_type="basket_size_increase",
                severity="observation",
                title="Larger purchases drove spending",
                category=basket["category"],
                merchant=basket["merchant"],
                change_amount=facts.average_transaction_change,
                change_percent=facts.average_transaction_change_percent,
                driver="basket_size_increase",
                recommendation="review_large_purchases",
                evidence=tuple(basket["evidence"]),
                priority=70,
            )
        )

    new_area = _behavior_pattern(facts, "new_spending_area")
    if new_area is not None:
        insights.append(
            FinancialInsight(
                insight_type="new_spending_area",
                severity="observation",
                title="A new spending area appeared",
                category=new_area["category"],
                merchant=new_area["merchant"],
                change_amount=next(
                    item.current_amount
                    for item in facts.category_changes
                    if item.category == new_area["category"]
                ),
                change_percent=None,
                driver="new_spending_area",
                recommendation="review_new_category",
                evidence=tuple(new_area["evidence"]),
                priority=78,
            )
        )

    distributed = _behavior_pattern(facts, "distributed_increase")
    if distributed is not None:
        insights.append(
            FinancialInsight(
                insight_type="distributed_increase",
                severity="observation",
                title="Spending increased across several areas",
                category=None,
                merchant=None,
                change_amount=facts.spending_change,
                change_percent=facts.spending_change_percent,
                driver="distributed_increase",
                recommendation="review_overall_spending",
                evidence=tuple(distributed["evidence"]),
                priority=62,
            )
        )

    return insights


def generate_financial_insights(facts: FinancialFacts, limit: int = 3) -> list[dict[str, object]]:
    """Generate a small set of ranked, non-redundant financial discoveries."""

    candidates = [
        _build_category_spike_insight(facts),
        _build_frequency_insight(facts),
        _build_average_transaction_insight(facts),
        *_build_behavior_insights(facts),
        _build_change_insight(facts),
    ]
    insights = [item for item in candidates if item is not None]
    insights.sort(key=lambda item: item.priority, reverse=True)
    return [item.to_dict() for item in insights[: max(0, limit)]]
