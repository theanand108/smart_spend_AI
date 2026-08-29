"""Flask blueprint for statement imports.

The blueprint is intentionally thin: parsing and persistence remain in the
statement_importer and statement_import_service modules so imported debit
transactions continue through the existing V2 persistence hook and credits
remain isolated as received money.
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from .statement_import_service import import_statement
from .statement_importer import parse_statement


statement_import_bp = Blueprint("statement_import", __name__)

ALLOWED_EXTENSIONS = {"csv", "pdf"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _allowed_filename(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def register_statement_import(app, db, Transaction) -> None:
    """Register the import blueprint and its dependencies with the Flask app."""
    app.config.setdefault("MAX_CONTENT_LENGTH", MAX_UPLOAD_BYTES)
    app.extensions["statement_import_db"] = db
    app.extensions["statement_import_transaction_model"] = Transaction
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

        app = statement_import_bp._state.app if False else None
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("statement_import.import_statement_page"))
    except Exception:
        flash("Unable to read this statement. Make sure it is a supported PhonePe CSV or Google Pay PDF.", "danger")
        return redirect(url_for("statement_import.import_statement_page"))

    # Flask blueprints don't expose the registering app directly. The dependency
    # objects are stored on the active app's extensions by register_statement_import.
    from flask import current_app

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
