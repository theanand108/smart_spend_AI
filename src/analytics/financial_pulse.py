"""Rule-based Financial Pulse generation.

This module is intentionally UI-agnostic. It returns structured data that can be
rendered by templates, APIs, CLIs, or future AI-assisted layers without coupling
business rules to presentation code.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable

SIGNIFICANT_SPENDING_INCREASE_RATIO = Decimal("0.10")
LARGEST_CATEGORY_RATIO = Decimal("0.50")
LARGEST_TRANSACTION_RATIO = Decimal("0.40")
MIN_TRANSACTIONS_FOR_PATTERN = 5


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
            priority=1,
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
            priority=2,
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
            message=f"{context.top_category} accounts for most of your spending this month.",
            icon="pie-chart",
            priority=3,
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
            priority=4,
            rule="largest_transaction",
        )

    return None


def _limited_transaction_history_rule(context: PulseContext) -> FinancialPulse | None:
    if context.total_transactions < MIN_TRANSACTIONS_FOR_PATTERN:
        return _build_pulse(
            status="Neutral",
            message="We're still learning your spending patterns.",
            icon="activity",
            priority=5,
            rule="limited_transaction_history",
        )

    return None


def _default_pulse() -> FinancialPulse:
    return _build_pulse(
        status="Healthy",
        message="Your spending patterns look stable.",
        icon="shield-check",
        priority=6,
        rule="default",
    )


PULSE_RULES: tuple[PulseRule, ...] = (
    _spending_decreased_rule,
    _spending_increased_significantly_rule,
    _largest_category_rule,
    _largest_transaction_rule,
    _limited_transaction_history_rule,
)


def generate_financial_pulse(
    current_month_spending: int | float | str | Decimal | None,
    last_month_spending: int | float | str | Decimal | None,
    top_category: str | None = None,
    top_category_spending: int | float | str | Decimal | None = None,
    largest_transaction: int | float | str | Decimal | None = None,
    total_transactions: int | str | None = None,
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
    )

    for rule in PULSE_RULES:
        pulse = rule(context)
        if pulse is not None:
            return pulse.to_dict()

    return _default_pulse().to_dict()
