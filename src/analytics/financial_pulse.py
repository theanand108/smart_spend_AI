"""Rule-based Financial Pulse generation.

This module is intentionally UI-agnostic. It returns structured data that can be
rendered by templates, APIs, CLIs, or future AI-assisted layers without coupling
business rules to presentation code.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable

SIGNIFICANT_SPENDING_INCREASE_RATIO = Decimal("0.10")
# Consider a single category dominant when it exceeds 60% of spending
LARGEST_CATEGORY_RATIO = Decimal("0.60")
LARGEST_TRANSACTION_RATIO = Decimal("0.40")
MIN_TRANSACTIONS_FOR_PATTERN = 5

# Thresholds for optional heuristic rules
HIGH_DAILY_SPEND_THRESHOLD = Decimal("1000")
WEEKEND_DOMINANCE_RATIO = Decimal("0.50")
FREQUENT_MERCHANT_RATIO = Decimal("0.4")


@dataclass(frozen=True)
class FinancialPulse:
    """Structured Financial Pulse result."""

    status: str
    title: str
    message: str
    action_text: str
    icon: str
    priority: int
    rule: str

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


@dataclass(frozen=True)
class PulseContext:
    """Normalized input values used by Financial Pulse rules."""

    current_month_spending: Decimal
    last_month_spending: Decimal | None
    top_category: str | None
    top_category_spending: Decimal
    largest_transaction: Decimal
    total_transactions: int
    # Optional additional signals (may be None if caller doesn't provide)
    most_frequent_merchant_count: int | None = None
    most_frequent_merchant_ratio: Decimal | None = None
    weekend_spending_ratio: Decimal | None = None
    avg_daily_spend: Decimal | None = None


PulseRule = Callable[[PulseContext], FinancialPulse | None]


def _to_decimal(value: int | float | str | Decimal | None) -> Decimal | None:
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _to_int(value: int | str | None) -> int:
    if value is None:
        return 0

    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _build_pulse(
    *,
    status: str,
    message: str,
    icon: str,
    priority: int,
    rule: str,
    action_text: str = "See what's driving this",
) -> FinancialPulse:
    return FinancialPulse(
        status=status,
        title="Financial Pulse",
        message=message,
        action_text=action_text,
        icon=icon,
        priority=priority,
        rule=rule,
    )


def _spending_decreased_rule(context: PulseContext) -> FinancialPulse | None:
    if context.last_month_spending is None:
        return None

    if context.current_month_spending < context.last_month_spending:
        return _build_pulse(
            status="Healthy",
            message="You're spending less than this point last month.",
            icon="check-circle",
            priority=6,
            rule="spending_decreased",
        )

    return None


def _spending_increased_significantly_rule(
    context: PulseContext,
) -> FinancialPulse | None:
    if context.last_month_spending is None or context.last_month_spending <= 0:
        return None

    increase_ratio = (
        context.current_month_spending - context.last_month_spending
    ) / context.last_month_spending

    if increase_ratio > SIGNIFICANT_SPENDING_INCREASE_RATIO:
        return _build_pulse(
            status="Attention",
            message="Your spending is noticeably higher than last month.",
            icon="exclamation-circle",
            priority=4,
            rule="spending_increased_significantly",
        )

    return None


def _largest_category_rule(context: PulseContext) -> FinancialPulse | None:
    if context.current_month_spending <= 0 or not context.top_category:
        return None

    category_ratio = context.top_category_spending / context.current_month_spending

    if category_ratio > LARGEST_CATEGORY_RATIO:
        return _build_pulse(
            status="Opportunity",
            message=f"{context.top_category} accounts for a large share of spending this month.",
            icon="pie-chart",
            priority=8,
            rule="largest_category",
        )

    return None


def _largest_transaction_rule(context: PulseContext) -> FinancialPulse | None:
    if context.current_month_spending <= 0:
        return None

    transaction_ratio = context.largest_transaction / context.current_month_spending

    if transaction_ratio > LARGEST_TRANSACTION_RATIO:
        return _build_pulse(
            status="Attention",
            message="One transaction represents a large portion of this month's spending.",
            icon="receipt",
            priority=7,
            rule="largest_transaction",
        )

    return None


def _limited_transaction_history_rule(context: PulseContext) -> FinancialPulse | None:
    if context.total_transactions < MIN_TRANSACTIONS_FOR_PATTERN:
        return _build_pulse(
            status="Neutral",
            message="We're still learning your spending patterns.",
            icon="activity",
            priority=12,
            rule="limited_transaction_history",
        )

    return None


def _default_pulse() -> FinancialPulse:
    return _build_pulse(
        status="Healthy",
        message="Your spending patterns look stable.",
        icon="shield-check",
        priority=99,
        rule="default",
    )


def _no_activity_rule(context: PulseContext) -> FinancialPulse | None:
    # No recorded spending or transactions this month
    if context.total_transactions == 0 or context.current_month_spending == Decimal("0"):
        return _build_pulse(
            status="Neutral",
            message="No spending recorded this month.",
            icon="minus-circle",
            priority=1,
            rule="no_activity",
        )


def _first_transaction_rule(context: PulseContext) -> FinancialPulse | None:
    if context.total_transactions == 1:
        return _build_pulse(
            status="Neutral",
            message="First transaction recorded this month.",
            icon="plus-circle",
            priority=2,
            rule="first_transaction",
        )


def _few_transactions_rule(context: PulseContext) -> FinancialPulse | None:
    if 1 < context.total_transactions <= 3:
        return _build_pulse(
            status="Neutral",
            message="Only a few transactions recorded this month.",
            icon="info",
            priority=3,
            rule="few_transactions",
        )


def _spending_increased_rule(context: PulseContext) -> FinancialPulse | None:
    if context.last_month_spending is None or context.last_month_spending <= 0:
        return None

    if context.current_month_spending > context.last_month_spending:
        return _build_pulse(
            status="Attention",
            message="Spending is higher than last month.",
            icon="arrow-up",
            priority=5,
            rule="spending_increased",
        )


def _one_merchant_frequent_rule(context: PulseContext) -> FinancialPulse | None:
    # Requires caller to provide most_frequent_merchant_ratio
    if context.most_frequent_merchant_ratio is None:
        return None

    if context.most_frequent_merchant_ratio >= FREQUENT_MERCHANT_RATIO:
        return _build_pulse(
            status="Opportunity",
            message="A single merchant appears frequently in your transactions.",
            icon="user-check",
            priority=9,
            rule="frequent_merchant",
        )


def _weekend_spending_dominates_rule(context: PulseContext) -> FinancialPulse | None:
    # Requires caller to provide weekend_spending_ratio
    if context.weekend_spending_ratio is None:
        return None

    if context.weekend_spending_ratio > WEEKEND_DOMINANCE_RATIO:
        return _build_pulse(
            status="Observation",
            message="Weekend spending represents a larger share of this month's expenses.",
            icon="calendar-week",
            priority=10,
            rule="weekend_dominant",
        )


def _high_daily_average_rule(context: PulseContext) -> FinancialPulse | None:
    if context.avg_daily_spend is None:
        return None

    if context.avg_daily_spend >= HIGH_DAILY_SPEND_THRESHOLD:
        return _build_pulse(
            status="Attention",
            message="Daily average spending is higher than usual.",
            icon="trending-up",
            priority=11,
            rule="high_daily_average",
        )


PULSE_RULES: tuple[PulseRule, ...] = (
    _no_activity_rule,
    _first_transaction_rule,
    _few_transactions_rule,
    _spending_increased_significantly_rule,
    _spending_increased_rule,
    _spending_decreased_rule,
    _largest_transaction_rule,
    _largest_category_rule,
    _one_merchant_frequent_rule,
    _weekend_spending_dominates_rule,
    _high_daily_average_rule,
    _limited_transaction_history_rule,
)


def generate_financial_pulse(
    current_month_spending: int | float | str | Decimal | None,
    last_month_spending: int | float | str | Decimal | None,
    top_category: str | None = None,
    top_category_spending: int | float | str | Decimal | None = None,
    largest_transaction: int | float | str | Decimal | None = None,
    total_transactions: int | str | None = None,
    # Optional additional signals
    most_frequent_merchant_count: int | str | None = None,
    most_frequent_merchant_ratio: int | float | str | Decimal | None = None,
    weekend_spending_ratio: int | float | str | Decimal | None = None,
    avg_daily_spend: int | float | str | Decimal | None = None,
) -> dict[str, str | int]:
    """Generate a rule-based Financial Pulse.

    Rules are evaluated in order. The first matching rule returns the pulse.
    If no rule matches, a neutral/default pulse is returned.
    """

    context = PulseContext(
        current_month_spending=_to_decimal(current_month_spending) or Decimal("0"),
        last_month_spending=_to_decimal(last_month_spending),
        top_category=top_category if top_category and top_category != "N/A" else None,
        top_category_spending=_to_decimal(top_category_spending) or Decimal("0"),
        largest_transaction=_to_decimal(largest_transaction) or Decimal("0"),
        total_transactions=_to_int(total_transactions),
        most_frequent_merchant_count=_to_int(most_frequent_merchant_count) or None,
        most_frequent_merchant_ratio=_to_decimal(most_frequent_merchant_ratio),
        weekend_spending_ratio=_to_decimal(weekend_spending_ratio),
        avg_daily_spend=_to_decimal(avg_daily_spend),
    )

    for rule in PULSE_RULES:
        pulse = rule(context)
        if pulse is not None:
            return pulse.to_dict()

    return _default_pulse().to_dict()
