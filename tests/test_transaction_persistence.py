from sqlalchemy import Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from src.intelligence.persistence import install


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_name: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    install()
    return Session(engine)


def test_new_transaction_uses_v2_semantic_categorization():
    session = make_session()

    transaction = Transaction(
        merchant_name="Local Pump",
        amount=1200,
        payment_method="upi",
        notes="filled up the tank before the trip",
    )
    session.add(transaction)
    session.commit()

    assert transaction.category == "Travel & Transport"


def test_generic_note_does_not_create_false_category():
    session = make_session()

    transaction = Transaction(
        merchant_name="Unknown Person",
        amount=500,
        payment_method="upi",
        notes="payment",
    )
    session.add(transaction)
    session.commit()

    assert transaction.category == "Unknown"


def test_edit_recalculates_and_replaces_stale_category():
    session = make_session()

    transaction = Transaction(
        merchant_name="Personal Contact",
        amount=350,
        payment_method="upi",
        notes="dinner at the college canteen",
    )
    session.add(transaction)
    session.commit()
    assert transaction.category == "Food & Dining"

    transaction.notes = "metro recharge for the week"
    session.commit()

    # The current transaction is excluded from its own history, so changing the
    # note re-runs V2 against the new purpose rather than reusing the stale
    # category from before the edit.
    assert transaction.category == "Travel & Transport"
