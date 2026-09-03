"""Deterministic financial facts for the intelligence layer.

This module deliberately contains no UI or language-generation logic. It turns
transaction records into auditable numbers that a later reasoning layer can
use to answer: what changed, what drove it, and how significant was it?
"""

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Sequence

IGNORED_CATEGORIES = {None, "", "Unknown", "Others"}


@dataclass(frozen=True)
class CategoryChange:
    category: str
    current_amount: Decimal
    previous_amount: Decimal
    amount_change: Decimal
    change_percent: Decimal | None


@dataclass(frozen=True)
class MerchantChange:
    merchant: str
    current_amount: Decimal
    previous_amount: Decimal
    amount_change: Decimal
    current_count: int
    previous_count: int


@dataclass(frozen=True)
class FinancialFacts:
    """Auditable facts derived from two transaction periods."""

    current_spending: Decimal
    previous_spending: Decimal
    spending_change: Decimal
    spending_change_percent: Decimal | None
    current_transaction_count: int
    previous_transaction_count: int
    transaction_count_change: int
    transaction_count_change_percent: Decimal | None
    current_average_transaction: Decimal
    previous_average_transaction: Decimal
    average_transaction_change: Decimal
    average_transaction_change_percent: Decimal | None
    current_categories: dict[str, Decimal]
    previous_categories: dict[str, Decimal]
    category_changes: tuple[CategoryChange, ...]
    merchant_changes: tuple[MerchantChange, ...]
    largest_current_transaction: dict[str, object] | None
    top_current_category: str | None
    top_current_category_amount: Decimal

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _text(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def _category(transaction: object) -> str | None:
    value = getattr(transaction, "category", None)
    text = str(value).strip() if value is not None else ""
    return None if text in IGNORED_CATEGORIES else text


def _merchant(transaction: object) -> str:
    return _text(getattr(transaction, "merchant_name", None), "Unknown merchant")


def _amount(transaction: object) -> Decimal:
    return _decimal(getattr(transaction, "amount", 0))


def _sum_by(transactions: Iterable[object], key_fn) -> dict[str, Decimal]:
    totals: defaultdict[str, Decimal] = defaultdict(Decimal)
    for transaction in transactions:
        amount = _amount(transaction)
        if amount <= 0:
            continue
        key = key_fn(transaction)
        if key is not None:
            totals[key] += amount
    return dict(totals)


def _count_by(transactions: Iterable[object], key_fn) -> dict[str, int]:
    counts: defaultdict[str, int] = defaultdict(int)
    for transaction in transactions:
        key = key_fn(transaction)
        if key is not None:
            counts[key] += 1
    return dict(counts)


def _percent_change(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None
    return ((current - previous) / previous) * Decimal("100")


def _average(transactions: Sequence[object]) -> Decimal:
    if not transactions:
        return Decimal("0")
    return sum((_amount(t) for t in transactions), Decimal("0")) / Decimal(len(transactions))


def _category_changes(
    current: dict[str, Decimal], previous: dict[str, Decimal]
) -> tuple[CategoryChange, ...]:
    changes = []
    for category in set(current) | set(previous):
        current_amount = current.get(category, Decimal("0"))
        previous_amount = previous.get(category, Decimal("0"))
        change = current_amount - previous_amount
        changes.append(
            CategoryChange(
                category=category,
                current_amount=current_amount,
                previous_amount=previous_amount,
                amount_change=change,
                change_percent=_percent_change(current_amount, previous_amount),
            )
        )
    return tuple(sorted(changes, key=lambda item: abs(item.amount_change), reverse=True))


def _merchant_changes(
    current: Sequence[object], previous: Sequence[object]
) -> tuple[MerchantChange, ...]:
    current_amounts = _sum_by(current, _merchant)
    previous_amounts = _sum_by(previous, _merchant)
    current_counts = _count_by(current, _merchant)
    previous_counts = _count_by(previous, _merchant)

    changes = []
    for merchant in set(current_amounts) | set(previous_amounts):
        changes.append(
            MerchantChange(
                merchant=merchant,
                current_amount=current_amounts.get(merchant, Decimal("0")),
                previous_amount=previous_amounts.get(merchant, Decimal("0")),
                amount_change=current_amounts.get(merchant, Decimal("0"))
                - previous_amounts.get(merchant, Decimal("0")),
                current_count=current_counts.get(merchant, 0),
                previous_count=previous_counts.get(merchant, 0),
            )
        )
    return tuple(sorted(changes, key=lambda item: abs(item.amount_change), reverse=True))


def _largest_transaction(transactions: Sequence[object]) -> dict[str, object] | None:
    positive = [t for t in transactions if _amount(t) > 0]
    if not positive:
        return None
    transaction = max(positive, key=_amount)
    return {
        "amount": _amount(transaction),
        "merchant": _merchant(transaction),
        "category": _category(transaction),
        "date": getattr(transaction, "date", None),
    }


def build_financial_facts(
    current_transactions: Iterable[object],
    previous_transactions: Iterable[object],
) -> FinancialFacts:
    """Build deterministic facts from current and comparison-period expenses.

    The function accepts ORM objects, dataclasses, or simple test doubles as
    long as they expose ``amount``, ``merchant_name`` and optionally ``category``
    and ``date``. No database queries are performed here.
    """

    current = tuple(current_transactions)
    previous = tuple(previous_transactions)

    current_spending = sum((_amount(t) for t in current), Decimal("0"))
    previous_spending = sum((_amount(t) for t in previous), Decimal("0"))
    spending_change = current_spending - previous_spending

    current_count = len(current)
    previous_count = len(previous)
    count_change = current_count - previous_count

    current_avg = _average(current)
    previous_avg = _average(previous)
    avg_change = current_avg - previous_avg

    current_categories = _sum_by(current, _category)
    previous_categories = _sum_by(previous, _category)

    top_category, top_amount = (None, Decimal("0"))
    if current_categories:
        top_category, top_amount = max(current_categories.items(), key=lambda item: item[1])

    return FinancialFacts(
        current_spending=current_spending,
        previous_spending=previous_spending,
        spending_change=spending_change,
        spending_change_percent=_percent_change(current_spending, previous_spending),
        current_transaction_count=current_count,
        previous_transaction_count=previous_count,
        transaction_count_change=count_change,
        transaction_count_change_percent=_percent_change(
            Decimal(current_count), Decimal(previous_count)
        ),
        current_average_transaction=current_avg,
        previous_average_transaction=previous_avg,
        average_transaction_change=avg_change,
        average_transaction_change_percent=_percent_change(current_avg, previous_avg),
        current_categories=current_categories,
        previous_categories=previous_categories,
        category_changes=_category_changes(current_categories, previous_categories),
        merchant_changes=_merchant_changes(current, previous),
        largest_current_transaction=_largest_transaction(current),
        top_current_category=top_category,
        top_current_category_amount=top_amount,
    )
