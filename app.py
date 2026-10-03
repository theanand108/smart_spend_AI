from calendar import monthrange, month_name
import csv
import io
import os

from dotenv import load_dotenv

load_dotenv()

# pyright: reportMissingImports=false
from flask import Flask, request, render_template, redirect, flash, get_flashed_messages, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, or_, text
from datetime import datetime
from functools import wraps
from secrets import token_urlsafe
from werkzeug.security import check_password_hash, generate_password_hash
from clerk_backend_api import Clerk
from clerk_backend_api import AuthenticateRequestOptions, authenticate_request
from src.analytics.financial_facts import build_financial_facts
from src.analytics.financial_pulse import generate_financial_pulse
from src.analytics.insight_engine import generate_financial_insights
from src.statement_import_web import register_statement_import

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or token_urlsafe(48)

# Database configuration
database_url = os.environ.get("DATABASE_URL", "sqlite:///smart_spend.db")

# Render/PostgreSQL may provide the generic `postgresql://` URL.
# Explicitly use psycopg 3, which is the PostgreSQL driver installed by
# `psycopg[binary]`.
if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
app.config["CLERK_SECRET_KEY"] = os.environ.get("CLERK_SECRET_KEY")
app.config["CLERK_JWT_KEY"] = os.environ.get("CLERK_JWT_KEY")
app.config["CLERK_PUBLISHABLE_KEY"] = (
    os.environ.get("CLERK_PUBLISHABLE_KEY")
    or os.environ.get("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
)
app.config["CLERK_AUTHORIZED_PARTIES"] = [
    part.strip()
    for part in os.environ.get("CLERK_AUTHORIZED_PARTIES", "").split(",")
    if part.strip()
]

# Initialize SQLAlchemy
db = SQLAlchemy(app)


def current_user_id():
    return session.get("user_id")


def current_user():
    user_id = current_user_id()
    return db.session.get(User, user_id) if user_id else None

