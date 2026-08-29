from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session

from src.intelligence.persistence import install
from src.statement_import_service import import_statement
from src.statement_importer import ImportedTransaction, StatementImportResult


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    merchant_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=True)
    payment_method = Column(String(50))
    notes = Column(String(200))


install()


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_import_separates_debits_from_received_money():
    session = make_session()
    result = StatementImportResult(
        (
            ImportedTransaction(
                datetime(2026, 8, 1, 10, 0),
                "EKART",
                369,
                "debit",
                "phonepe",
                "debit-1",
            ),
            ImportedTransaction(
                datetime(2026, 8, 1, 11, 0),
                "MUKUND KUSHWAHA",
                5000,
                "credit",
                "phonepe",
                "credit-1",
            ),
        )
    )

    summary = import_statement(session, Transaction, result)

    assert summary["imported_expenses"] == 1
    assert summary["imported_received"] == 1
    assert session.query(Transaction).count() == 1
    assert session.query(Transaction).one().amount == 369

    received = session.execute(
        text("SELECT amount, merchant_name FROM received_money")
    ).all()
    assert received == [(5000.0, "MUKUND KUSHWAHA")]


def test_import_skips_the_same_source_transaction_on_repeat_import():
    session = make_session()
    item = ImportedTransaction(
        datetime(2026, 8, 1, 10, 0),
        "EKART",
        369,
        "debit",
        "phonepe",
        "same-id",
    )
    result = StatementImportResult((item,))

    first = import_statement(session, Transaction, result)
    second = import_statement(session, Transaction, result)

    assert first["imported_expenses"] == 1
    assert second["skipped_duplicates"] == 1
    assert session.query(Transaction).count() == 1
