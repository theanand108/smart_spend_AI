"""Flask blueprint for statement imports.

The blueprint is intentionally thin: parsing and persistence remain in the
statement_importer and statement_import_service modules so imported debit
transactions continue through the existing V2 persistence hook and credits
remain isolated as received money.
"""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import text, update
from werkzeug.utils import secure_filename

from .intelligence.attention import build_attention_queue
from .statement_import_service import import_statement
from .statement_importer import parse_statement


statement_import_bp = Blueprint("statement_import", __name__)

ALLOWED_EXTENSIONS = {"csv", "pdf"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
REVIEW_CATEGORIES = (
    "Food & Dining",
    "Travel & Transport",
    "Entertainment",
    "Groceries",
    "Bills & Utilities",
    "Shopping",
    "Health & Fitness",
    "Others",
)


def _allowed_filename(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def register_statement_import(app, db, Transaction) -> None:
    """Register the import blueprint and its dependencies with the Flask app."""
    app.config.setdefault("MAX_CONTENT_LENGTH", MAX_UPLOAD_BYTES)
    app.extensions["statement_import_db"] = db
    app.extensions["statement_import_transaction_model"] = Transaction

    @app.context_processor
    def inject_received_money_summary():
        if request.endpoint != "dashboard1":
            return {}

        month = request.view_args.get("month") if request.view_args else None
        try:
            month = int(month) if month is not None else datetime.now().month
        except (TypeError, ValueError):
            month = datetime.now().month
        if not 1 <= month <= 12:
            month = datetime.now().month

        year = datetime.now().year
        try:
            row = db.session.execute(
                text(
                    "SELECT COALESCE(SUM(amount), 0), COUNT(*) "
                    "FROM received_money "
                    "WHERE strftime('%Y', transaction_date) = :year "
                    "AND strftime('%m', transaction_date) = :month"
                ),
                {"year": str(year), "month": f"{month:02d}"},
            ).first()
        except Exception:
            return {"received_money_total": 0.0, "received_money_count": 0}

        return {
            "received_money_total": float(row[0] or 0) if row else 0.0,
            "received_money_count": int(row[1] or 0) if row else 0,
        }

    if statement_import_bp.name not in app.blueprints:
        app.register_blueprint(statement_import_bp)


@statement_import_bp.route("/import", methods=["GET", "POST"])
def import_statement_page():
    if request.method == "GET":
        return render_template("statement_import.html", flash_messages=[])

    uploaded = request.files.get("statement")
    if not uploaded or not uploaded.filename:
        flash("Choose a PhonePe CSV or Google Pay PDF to import.", "warning")
        return redirect(url_for("statement_import.import_statement_page"))

    filename = secure_filename(uploaded.filename)
    if not _allowed_filename(filename):
        flash("Unsupported file type. Upload a CSV or PDF statement.", "danger")
        return redirect(url_for("statement_import.import_statement_page"))

    try:
        data = uploaded.read()
        if not data:
            raise ValueError("The uploaded statement is empty.")

        result = parse_statement(filename, data)
        if not result.transactions:
            detail = result.skipped_rows[0] if result.skipped_rows else "No supported transactions were found."
            raise ValueError(f"No transactions could be imported. {detail}")
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("statement_import.import_statement_page"))
    except Exception:
        flash("Unable to read this statement. Make sure it is a supported PhonePe CSV or Google Pay PDF.", "danger")
        return redirect(url_for("statement_import.import_statement_page"))

    db = current_app.extensions["statement_import_db"]
    Transaction = current_app.extensions["statement_import_transaction_model"]

    try:
        summary = import_statement(db.session, Transaction, result)
    except Exception:
        db.session.rollback()
        flash("The statement could not be saved. No imported spending data was committed.", "danger")
        return redirect(url_for("statement_import.import_statement_page"))

    expense_text = f"{summary['imported_expenses']} spending transactions"
    received_text = f"{summary['imported_received']} received transactions"
    duplicate_text = (
        f" {summary['skipped_duplicates']} duplicates skipped."
        if summary["skipped_duplicates"]
        else ""
    )
    skipped_text = (
        f" {summary['skipped_rows']} invalid rows skipped."
        if summary["skipped_rows"]
        else ""
    )
    flash(f"Imported {expense_text} and {received_text}.{duplicate_text}{skipped_text}", "success")
    return redirect(url_for("dashboard1"))


@statement_import_bp.route("/dashboard/attention", methods=["GET"])
def dashboard_attention():
    """Return the dashboard's unresolved V2 intelligence states as a partial."""
    db = current_app.extensions["statement_import_db"]
    Transaction = current_app.extensions["statement_import_transaction_model"]

    try:
        month = int(request.args.get("month", datetime.now().month))
    except (TypeError, ValueError):
        month = datetime.now().month
    if not 1 <= month <= 12:
        month = datetime.now().month

    year = datetime.now().year
    transactions = (
        Transaction.query.filter(
            db.extract("month", Transaction.date) == month,
            db.extract("year", Transaction.date) == year,
        )
        .order_by(Transaction.date.desc())
        .all()
    )
    attention = build_attention_queue(transactions)
    return render_template(
        "_attention.html",
        attention=attention,
        review_categories=REVIEW_CATEGORIES,
    )


@statement_import_bp.route("/dashboard/attention/<int:transaction_id>", methods=["POST"])
def resolve_dashboard_attention(transaction_id: int):
    """Persist one explicit user category correction and return to the dashboard."""
    db = current_app.extensions["statement_import_db"]
    Transaction = current_app.extensions["statement_import_transaction_model"]
    category = request.form.get("category", "").strip()
    next_url = request.form.get("next") or "/dashboard"
    if not next_url.startswith("/"):
        next_url = "/dashboard"

    transaction = db.session.get(Transaction, transaction_id)
    if not transaction:
        flash("That transaction could not be found.", "danger")
        return redirect(next_url)

    if category not in REVIEW_CATEGORIES:
        flash("Choose a valid category before saving.", "warning")
        return redirect(next_url)

    try:
        result = db.session.execute(
            update(Transaction)
            .where(Transaction.id == transaction_id)
            .values(category=category)
        )
        if result.rowcount != 1:
            db.session.rollback()
            flash("That transaction could not be updated.", "danger")
            return redirect(next_url)

        db.session.commit()
        flash(f"{transaction.merchant_name} was categorized as {category}.", "success")
    except Exception:
        db.session.rollback()
        flash("Unable to save that category correction.", "danger")

    return redirect(next_url)
