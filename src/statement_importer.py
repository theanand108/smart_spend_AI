"""Statement import parsing for Smart Spend AI.

This module is deliberately separate from the spending intelligence pipeline.
It turns provider statements into a small canonical representation; callers are
responsible for sending debit rows through V2 categorization and storing credit
rows as received money.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ImportedTransaction:
    date: datetime
    merchant_name: str
    amount: float
    direction: str  # "debit" or "credit"
    source: str
    source_transaction_id: str | None = None
    payment_method: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class StatementImportResult:
    transactions: tuple[ImportedTransaction, ...]
    skipped_rows: tuple[str, ...] = ()

    @property
    def expenses(self) -> tuple[ImportedTransaction, ...]:
        return tuple(t for t in self.transactions if t.direction == "debit")

    @property
    def received(self) -> tuple[ImportedTransaction, ...]:
        return tuple(t for t in self.transactions if t.direction == "credit")


_HEADER_ALIASES = {
    "date": {"date", "transactiondate", "datetime", "dateandtime"},
    "time": {"time", "transactiontime"},
    "details": {
        "transactiondetails", "transactiondetail", "description", "details",
        "merchant", "merchantname", "payee", "recipient",
    },
    "amount": {"amount", "transactionamount", "value"},
    "transaction_type": {"transactiontype", "type", "direction", "debitcredit"},
    "transaction_id": {"transactionid", "upiid", "upitransactionid", "referenceid", "reference"},
    "utr": {"utr", "utrnumber"},
    "payment_method": {"paymentmethod", "instrument", "creditdebitinstrument", "paidby", "creditedto"},
}


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _header_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", _clean(value).lower())


def _find_column(headers: list[str], canonical: str) -> int | None:
    aliases = _HEADER_ALIASES[canonical]
    normalized = [_header_key(header) for header in headers]
    for index, header in enumerate(normalized):
        if header in aliases:
            return index
    return None


def _parse_amount(value: object) -> float:
    cleaned = _clean(value).replace(",", "")
    cleaned = cleaned.replace("₹", "").replace("INR", "").strip()
    return float(cleaned)


def _parse_date(date_value: str, time_value: str | None = None) -> datetime:
    date_value = _clean(date_value)
    time_value = _clean(time_value)
    combined = f"{date_value} {time_value}".strip()

    formats = (
        "%d %b, %Y %I:%M %p",
        "%d %b, %Y %I:%M%p",
        "%d%b,%Y %I:%M %p",
        "%d%b,%Y %I:%M%p",
        "%d %B, %Y %I:%M %p",
        "%b %d, %Y %I:%M %p",
        "%b %d, %Y %I:%M%p",
        "%b %d, %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported transaction date: {combined}")


def _direction_from_values(details: str, transaction_type: str) -> str | None:
    details_lower = details.lower()
    type_lower = transaction_type.lower()
    if "received" in details_lower or "credit" in type_lower or "received" in type_lower:
        return "credit"
    if "paid to" in details_lower or "debit" in type_lower or "sent" in type_lower:
        return "debit"
    return None


def _merchant_from_details(details: str) -> str:
    cleaned = _clean(details)
    cleaned = re.sub(r"^(paid\s*to|received\s*from)\s*", "", cleaned, flags=re.I)
    return cleaned.strip()


def parse_csv_text(text: str, source: str = "csv") -> StatementImportResult:
    """Parse a structured CSV using provider-neutral column aliases."""
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    header_index = None
    for index, row in enumerate(rows):
        keys = {_header_key(cell) for cell in row}
        if "amount" in keys and ({"date", "transactiondate", "datetime"} & keys):
            header_index = index
            break

    if header_index is None:
        raise ValueError("No supported transaction header row was found in the CSV.")

    headers = rows[header_index]
    date_index = _find_column(headers, "date")
    time_index = _find_column(headers, "time")
    details_index = _find_column(headers, "details")
    amount_index = _find_column(headers, "amount")
    type_index = _find_column(headers, "transaction_type")
    transaction_id_index = _find_column(headers, "transaction_id")
    if transaction_id_index is None:
        transaction_id_index = _find_column(headers, "utr")
    payment_index = _find_column(headers, "payment_method")

    if date_index is None or details_index is None or amount_index is None:
        raise ValueError("CSV must contain date, transaction details/merchant, and amount columns.")

    parsed: list[ImportedTransaction] = []
    skipped: list[str] = []

    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(_clean(cell) for cell in row):
            continue
        try:
            details = _clean(row[details_index])
            amount = _parse_amount(row[amount_index])
            transaction_type = _clean(row[type_index]) if type_index is not None and type_index < len(row) else ""
            direction = _direction_from_values(details, transaction_type)
            if direction is None:
                raise ValueError("could not determine debit/credit direction")
            merchant = _merchant_from_details(details)
            if not merchant:
                raise ValueError("merchant/transaction details are empty")

            date = _parse_date(
                row[date_index],
                row[time_index] if time_index is not None and time_index < len(row) else None,
            )
            source_id = (
                _clean(row[transaction_id_index])
                if transaction_id_index is not None and transaction_id_index < len(row)
                else None
            ) or None
            payment_method = (
                _clean(row[payment_index])
                if payment_index is not None and payment_index < len(row)
                else None
            ) or None

            parsed.append(
                ImportedTransaction(
                    date=date,
                    merchant_name=merchant,
                    amount=amount,
                    direction=direction,
                    source=source,
                    source_transaction_id=source_id,
                    payment_method=payment_method,
                    note=details,
                )
            )
        except (IndexError, ValueError) as exc:
            skipped.append(f"row {row_number}: {exc}")

    return StatementImportResult(tuple(parsed), tuple(skipped))


def parse_phonepe_csv(text: str) -> StatementImportResult:
    return parse_csv_text(text, source="phonepe")


_GPAY_DATE = re.compile(r"(\d{2}\s*[A-Za-z]{3},\s*\d{4})")
_GPAY_TIME = re.compile(r"(\d{2}:\d{2}\s*(?:AM|PM))", re.I)
_GPAY_UPI_ID = re.compile(r"UPI\s*Transaction\s*ID\s*:\s*([A-Za-z0-9]+)", re.I)
_GPAY_AMOUNT = re.compile(r"₹\s*([\d,]+(?:\.\d+)?)")


def parse_google_pay_text(text: str) -> StatementImportResult:
    """Parse the text extracted from a native Google Pay transaction PDF."""
    starts = list(_GPAY_DATE.finditer(text))
    parsed: list[ImportedTransaction] = []
    skipped: list[str] = []

    for index, match in enumerate(starts):
        block_end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start() : block_end]
        date_text = match.group(1)
        time_match = _GPAY_TIME.search(block)
        if not time_match:
            continue

        try:
            amount_matches = list(_GPAY_AMOUNT.finditer(block))
            if not amount_matches:
                raise ValueError("amount not found")
            amount = _parse_amount(amount_matches[-1].group(1))

            direction_match = re.search(
                r"\b(Paid\s*to|Received\s*from)\s*(.+?)\s*UPI\s*Transaction",
                block,
                re.I,
            )
            if not direction_match:
                raise ValueError("Google Pay recipient/sender not found")
            direction_phrase = _clean(direction_match.group(1))
            direction = "credit" if direction_phrase.lower().startswith("received") else "debit"
            merchant = _clean(direction_match.group(2))

            upi_match = _GPAY_UPI_ID.search(block)
            source_id = upi_match.group(1) if upi_match else None
            parsed.append(
                ImportedTransaction(
                    date=_parse_date(date_text, time_match.group(1)),
                    merchant_name=merchant,
                    amount=amount,
                    direction=direction,
                    source="google_pay",
                    source_transaction_id=source_id,
                    note=f"{direction_phrase} {merchant}",
                )
            )
        except ValueError as exc:
            skipped.append(f"transaction near {date_text}: {exc}")

    return StatementImportResult(tuple(parsed), tuple(skipped))


def parse_google_pay_pdf(data: bytes) -> StatementImportResult:
    """Extract and parse text from a native Google Pay PDF."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is declared in requirements
        raise RuntimeError("Google Pay PDF import requires the pypdf package.") from exc

    reader = PdfReader(io.BytesIO(data))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return parse_google_pay_text(text)


def parse_statement(filename: str, data: bytes) -> StatementImportResult:
    """Choose the supported parser from a statement filename."""
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return parse_google_pay_pdf(data)
    if lower_name.endswith(".csv"):
        text = data.decode("utf-8-sig", errors="replace")
        return parse_csv_text(text)
    raise ValueError("Unsupported statement format. Upload CSV or Google Pay PDF.")
