from calendar import monthrange, month_name

# pyright: reportMissingImports=false
from flask import Flask, request, render_template, redirect, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from datetime import datetime
from src.analytics.financial_pulse import generate_financial_pulse

app = Flask(__name__)
app.secret_key = "smart-spend-toast-secret"

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///smart_spend.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)


class Transaction(db.Model):
    try:
        id = db.Column(db.Integer, primary_key=True)
        date = db.Column(db.DateTime, default=datetime.utcnow)
        merchant_name = db.Column(db.String, nullable=False)
        amount = db.Column(db.Float, nullable=False)
        category = db.Column(db.String(50), nullable=True)
        payment_method = db.Column(db.String(50))
        notes = db.Column(db.String(200))
    except Exception as e:
        print(f"Error defining Transaction model: {e}")

    def __repr__(self):

        return f"<Transaction {self.merchant_name}>"


def categorize(merchant):
    merchant = str(merchant).lower()

    if (
        "zomato" in merchant
        or "swiggy" in merchant
        or "starbucks" in merchant
        or "dominoz" in merchant
    ):
        return "Food & Dining"
    elif "uber" in merchant or "ola" in merchant or "petrol" in merchant:
        return "Travel & Transport"
    elif "netflix" in merchant or "spotify" in merchant or "bookmyshow" in merchant:
        return "Entertainment"
    elif "blinkit" in merchant or "kirana" in merchant:
        return "Groceries"
    elif "airtel" in merchant:
        return "Bills & Utilities"
    elif (
        "myntra" in merchant
        or "h&m" in merchant
        or "amazon" in merchant
        or "flipkart" in merchant
    ):
        return "Shopping"
    elif "gym" in merchant or "health" in merchant or "hospital" in merchant:
        return "Health & Fitness"
    else:
        return "Others"


def build_transaction_query(month, year, search_query=""):
    month_filters = [
        db.extract("month", Transaction.date) == month,
        db.extract("year", Transaction.date) == year,
    ]
    
    query = Transaction.query.filter(*month_filters)

    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Transaction.merchant_name.ilike(pattern),
                Transaction.notes.ilike(pattern),
                Transaction.category.ilike(pattern),
            )
        )

    return query

def get_spending_analytics(transaction_query):
    top_merchant_query = (
        transaction_query.with_entities(
            Transaction.merchant_name, db.func.sum(Transaction.amount).label("total")
        )
        .group_by(Transaction.merchant_name)
        .order_by(db.text("total DESC"))
        .first()
    )
    most_freqMerchant_query = (
        transaction_query.with_entities(
            Transaction.merchant_name, db.func.count(Transaction.id).label("total")
        )
        .group_by(Transaction.merchant_name)
        .order_by(db.text("total DESC"))
        .first()
    )
    largest_transaction = (
    transaction_query
    .with_entities(db.func.max(Transaction.amount))
    .scalar()
    )
    smallest_transaction = (
    transaction_query
    .with_entities(db.func.min(Transaction.amount))
    .scalar()
    )
    
    daily_spend = (
        transaction_query.with_entities(db.func.sum(Transaction.amount)).scalar()
    )
    days = (
        transaction_query.with_entities(db.func.count(Transaction.id)).scalar()
    )
    avg_daily_spend = daily_spend / days if days else 1
    
    most_freqMerchant = most_freqMerchant_query[0] if most_freqMerchant_query else "N/A"
    
    if top_merchant_query:
        top_merchant = top_merchant_query[0]
        top_merchant_amount = top_merchant_query[1]
    else:
        top_merchant = "N/A"
        top_merchant_amount = 0
    
    
    
    
    return {
        "top_merchant": top_merchant,
        "top_merchant_amount": top_merchant_amount,
        "most_frequent_merchant": most_freqMerchant,
        "largest_transaction": largest_transaction,
        "smallest_transaction": smallest_transaction,
        "avg_daily_spend": round(avg_daily_spend, 2)
    }


def format_currency(amount):
    amount = float(amount or 0)
    if amount.is_integer():
        return f"₹{int(amount):,}"
    return f"₹{amount:,.2f}"


def make_insight(title, value, supporting_text, priority_score):
    return {
        "title": title,
        "value": value,
        "supporting_text": supporting_text,
        "priority_score": priority_score,
    }


def biggest_money_destination_insight(context):
    if not context["merchant_amounts"] or not context["total_expense"]:
        return None

    merchant, amount = max(context["merchant_amounts"].items(), key=lambda item: item[1])
    if not merchant or amount <= 0:
        return None

    percent = (amount / context["total_expense"]) * 100
    return make_insight(
        "Biggest Money Destination",
        merchant,
        f"You spent {format_currency(amount)} here, about {percent:.0f}% of this month's spending.",
        90 + percent,
    )


def largest_transaction_insight(context):
    largest_transaction = context["largest_transaction"]
    if not largest_transaction:
        return None

    amount = float(largest_transaction.amount or 0)
    if amount <= 0:
        return None

    percent = (amount / context["total_expense"] * 100) if context["total_expense"] else 0
    merchant = largest_transaction.merchant_name or "one merchant"
    return make_insight(
        "Largest Transaction",
        format_currency(amount),
        f"Your biggest expense was at {merchant}, making up about {percent:.0f}% of this month's spending.",
        82 + percent,
    )


def most_frequent_merchant_insight(context):
    if not context["merchant_counts"]:
        return None

    merchant, count = max(context["merchant_counts"].items(), key=lambda item: item[1])
    if count <= 1:
        return None

    return make_insight(
        "Most Frequent Merchant",
        merchant,
        f"You had {count} transactions here this month.",
        72 + (count * 3),
    )


def highest_spending_category_insight(context):
    if context["top_category"] == "N/A" or context["top_category_amount"] <= 0:
        return None

    percent = (
        (context["top_category_amount"] / context["total_expense"]) * 100
        if context["total_expense"]
        else 0
    )
    return make_insight(
        "Highest Spending Category",
        context["top_category"],
        f"You spent {format_currency(context['top_category_amount'])} on this category, about {percent:.0f}% of the month.",
        76 + percent,
    )


def weekend_spending_pattern_insight(context):
    ratio = context["weekend_spending_ratio"]
    if ratio < 0.5:
        return None

    return make_insight(
        "Weekend Spending",
        f"{ratio * 100:.0f}% of your spending",
        "Most of your expenses happened during weekends.",
        70 + (ratio * 30),
    )


def small_purchase_habit_insight(context):
    if context["small_tx_count"] < 2 or context["small_tx_ratio"] < 0.5:
        return None

    return make_insight(
        "Small Purchase Habit",
        f"{context['small_tx_count']} small purchases",
        f"{context['small_tx_ratio'] * 100:.0f}% of your transactions were under ₹100.",
        64 + (context["small_tx_ratio"] * 25),
    )


def high_daily_average_insight(context):
    avg_daily_spend = context["calendar_avg_daily_spend"]
    if avg_daily_spend < 1000:
        return None

    return make_insight(
        "High Daily Average",
        f"{format_currency(avg_daily_spend)} per day",
        "Your daily average is running high for this month.",
        68 + min(avg_daily_spend / 100, 30),
    )


def few_transactions_this_month_insight(context):
    if not 1 < context["total_transactions"] <= 3:
        return None

    return make_insight(
        "Few Transactions This Month",
        f"{context['total_transactions']} transactions",
        "There are only a few expenses recorded, so trends may still change quickly.",
        62,
    )


def first_transaction_this_month_insight(context):
    if context["total_transactions"] != 1:
        return None

    return make_insight(
        "First Transaction This Month",
        "1 transaction",
        "This is the first expense recorded for the selected month.",
        66,
    )


INSIGHT_GENERATORS = [
    biggest_money_destination_insight,
    largest_transaction_insight,
    most_frequent_merchant_insight,
    highest_spending_category_insight,
    weekend_spending_pattern_insight,
    small_purchase_habit_insight,
    high_daily_average_insight,
    few_transactions_this_month_insight,
    first_transaction_this_month_insight,
]


def build_key_insights(context, limit=3):
    insights = []
    for generator in INSIGHT_GENERATORS:
        insight = generator(context)
        if insight:
            insights.append(insight)

    return sorted(
        insights,
        key=lambda insight: insight["priority_score"],
        reverse=True,
    )[:limit]


def get_category_totals_for_query(transaction_query):
    return {
        category or "Others": float(total or 0)
        for category, total in transaction_query.with_entities(
            Transaction.category,
            db.func.sum(Transaction.amount),
        )
        .group_by(Transaction.category)
        .all()
    }


def get_previous_month(month, year):
    if month == 1:
        return 12, year - 1
    return month - 1, year


def get_top_category_for_query(transaction_query):
    top_category_query = (
        transaction_query.with_entities(
            Transaction.category, db.func.sum(Transaction.amount).label("total")
        )
        .group_by(Transaction.category)
        .order_by(db.text("total DESC"))
        .first()
    )

    if not top_category_query:
        return "N/A", 0

    return top_category_query[0], top_category_query[1]


def format_percentage_change(current_value, previous_value):
    if previous_value == 0:
        return ""

    change = abs((current_value - previous_value) / previous_value) * 100
    return f"{change:.0f}%"


def format_numeric_change(current_value, previous_value):
    difference = abs(current_value - previous_value)
    if difference == 0:
        return "0"
    return f"{difference:g}"


def format_signed_currency(amount):
    sign = "+" if amount > 0 else "-" if amount < 0 else ""
    return f"{sign}{format_currency(abs(amount))}"


def get_change_details(current_value, previous_value, lower_is_better=False):
    if current_value == previous_value:
        return "→", "text-muted"

    improved = current_value < previous_value if lower_is_better else current_value > previous_value
    trend_indicator = "↓" if current_value < previous_value else "↑"
    trend_class = "text-success" if improved else "text-danger"
    return trend_indicator, trend_class


def build_comparison_row(
    metric_title,
    current_value,
    previous_value,
    previous_sort_value,
    current_sort_value,
    helper_text,
    difference_text="",
    lower_is_better=False,
):
    trend_indicator, trend_class = get_change_details(
        current_sort_value,
        previous_sort_value,
        lower_is_better=lower_is_better,
    )

    return {
        "metric_title": metric_title,
        "previous_value": previous_value,
        "current_value": current_value,
        "trend_indicator": trend_indicator,
        "trend_class": trend_class,
        "difference_text": difference_text,
        "helper_text": helper_text,
    }


def get_financial_health(financial_pulse, current_total, previous_total):
    rule = financial_pulse.get("rule")

    if rule == "spending_decreased":
        return "🟢 Excellent"
    if rule in {"default"} and current_total <= previous_total:
        return "🟢 Healthy"
    if rule in {
        "limited_transaction_history",
        "first_transaction",
        "few_transactions",
        "largest_category",
        "weekend_dominant",
        "frequent_merchant",
    }:
        return "🟡 Stable"
    if rule in {"spending_increased", "high_daily_average", "largest_transaction"}:
        return "🟠 Watching"
    if rule == "spending_increased_significantly":
        return "🔴 Needs Attention"
    if rule == "no_activity":
        return "🟡 Stable"

    return "🟢 Healthy"


def build_biggest_driver(current_category_totals, previous_category_totals, total_change):
    category_changes = []
    for category in set(current_category_totals) | set(previous_category_totals):
        current_amount = current_category_totals.get(category, 0)
        previous_amount = previous_category_totals.get(category, 0)
        category_changes.append((category, current_amount - previous_amount))

    if not category_changes:
        return {
            "category": "No category yet",
            "amount_change": format_signed_currency(0),
            "share_text": "Add more transactions to reveal what is driving changes.",
        }

    if total_change > 0:
        category, change = max(category_changes, key=lambda item: item[1])
        share = (change / total_change * 100) if change > 0 else 0
        share_text = f"{share:.0f}% of the total increase" if share else "No single category drove the increase"
    elif total_change < 0:
        category, change = min(category_changes, key=lambda item: item[1])
        share = (abs(change) / abs(total_change) * 100) if change < 0 else 0
        share_text = f"{share:.0f}% of the total decrease" if share else "Savings were spread across categories"
    else:
        category, change = max(category_changes, key=lambda item: abs(item[1]))
        share_text = "Spending was mostly unchanged overall"

    return {
        "category": category,
        "amount_change": format_signed_currency(change),
        "share_text": share_text,
    }


def build_pulse_recommendation(financial_pulse, biggest_driver, total_change):
    category = biggest_driver["category"]
    rule = financial_pulse.get("rule")

    if total_change < 0:
        return f"{category} spending looks healthy this month."
    if category == "Food & Dining" and total_change > 0:
        return "One fewer food delivery each week could save around ₹800."
    if category == "Travel & Transport" and total_change <= 0:
        return "Transportation spending looks healthy this month."
    if rule in {"spending_increased", "spending_increased_significantly"}:
        return f"Most of your increase came from {category}; a small weekly adjustment could keep next month steadier."
    if rule == "largest_transaction":
        return "One large purchase shaped this month, so the overall trend may settle down next month."
    if rule in {"first_transaction", "few_transactions", "limited_transaction_history"}:
        return "As you add more transactions, your pulse will become more useful."
    if category and category != "No category yet":
        return f"{category} is the main area to watch, but your pattern is still manageable."

    return "Your spending pattern looks steady; keep checking in as the month develops."


def build_financial_pulse_summary(
    *,
    financial_pulse,
    current_total,
    previous_total,
    current_category_totals,
    previous_category_totals,
):
    total_change = current_total - previous_total
    if previous_total:
        percent_change = (total_change / previous_total) * 100
        main_change_value = f"{percent_change:+.0f}%"
    elif current_total:
        main_change_value = "+100%"
    else:
        main_change_value = "0%"

    if total_change > 0:
        main_change_label = "Spending Increased"
    elif total_change < 0:
        main_change_label = "Spending Decreased"
    else:
        main_change_label = "Spending Stayed Stable"

    biggest_driver = build_biggest_driver(
        current_category_totals,
        previous_category_totals,
        total_change,
    )

    return {
        "health": get_financial_health(financial_pulse, current_total, previous_total),
        "main_change_value": main_change_value,
        "main_change_label": main_change_label,
        "current_total": format_currency(current_total),
        "previous_total": format_currency(previous_total),
        "biggest_driver": biggest_driver,
        "recommendation": build_pulse_recommendation(
            financial_pulse,
            biggest_driver,
            total_change,
        ),
        "cta_text": "Explore Details",
    }


def build_month_comparison_summary(
    *,
    current_total_expense,
    current_total_transactions,
    current_top_category,
    current_days_in_month,
    previous_total_expense,
    previous_total_transactions,
    previous_top_category,
    previous_days_in_month,
):
    if previous_total_transactions == 0:
        return None

    current_daily_average = current_total_expense / current_days_in_month
    previous_daily_average = previous_total_expense / previous_days_in_month
    spending_difference = abs(current_total_expense - previous_total_expense)
    daily_average_difference = abs(current_daily_average - previous_daily_average)

    if current_total_expense < previous_total_expense:
        spending_helper = f"You spent {format_currency(spending_difference)} less than last month."
    elif current_total_expense > previous_total_expense:
        spending_helper = f"You spent {format_currency(spending_difference)} more than last month."
    else:
        spending_helper = "Your spending stayed the same as last month."

    if current_total_transactions < previous_total_transactions:
        transaction_helper = f"You made {format_numeric_change(current_total_transactions, previous_total_transactions)} fewer transactions than last month."
    elif current_total_transactions > previous_total_transactions:
        transaction_helper = f"You made {format_numeric_change(current_total_transactions, previous_total_transactions)} more transactions than last month."
    else:
        transaction_helper = "Your transaction count stayed the same as last month."

    if current_top_category != previous_top_category:
        category_helper = f"{current_top_category} replaced {previous_top_category} as your largest category."
    else:
        category_helper = f"{current_top_category} stayed your largest category."

    if current_daily_average < previous_daily_average:
        daily_average_helper = f"Your average daily spending decreased by {format_currency(daily_average_difference)}."
    elif current_daily_average > previous_daily_average:
        daily_average_helper = f"Your average daily spending increased by {format_currency(daily_average_difference)}."
    else:
        daily_average_helper = "Your average daily spending stayed the same."

    return {
        "rows": [
            build_comparison_row(
                "Overall Spending",
                format_currency(current_total_expense),
                format_currency(previous_total_expense),
                previous_total_expense,
                current_total_expense,
                spending_helper,
                format_percentage_change(current_total_expense, previous_total_expense),
                lower_is_better=True,
            ),
            build_comparison_row(
                "Total Transactions",
                str(current_total_transactions),
                str(previous_total_transactions),
                previous_total_transactions,
                current_total_transactions,
                transaction_helper,
                format_numeric_change(current_total_transactions, previous_total_transactions),
                lower_is_better=True,
            ),
            build_comparison_row(
                "Top Category",
                current_top_category,
                previous_top_category,
                0,
                0,
                category_helper,
            ),
            build_comparison_row(
                "Average Spend per Day",
                format_currency(current_daily_average),
                format_currency(previous_daily_average),
                previous_daily_average,
                current_daily_average,
                daily_average_helper,
                format_percentage_change(current_daily_average, previous_daily_average),
                lower_is_better=True,
            ),
        ]
    }


@app.route("/submit_expense", methods=["POST"])
def submit():
    try:
        merchant_name = request.form.get("merchant_name")
        amount = request.form.get("amount")
        notes = request.form.get("notes")
        payment_method = request.form.get("payment_method")

        transaction = Transaction(
            merchant_name=merchant_name,
            amount=float(amount),
            category=categorize(merchant_name),
            notes=notes,
            payment_method=payment_method,
        )

        db.session.add(transaction)
        db.session.commit()

        flash("Transaction added successfully.", "success")
        # redirect back to simulate page and indicate the newly created transaction id
        return redirect(f"/simulateATransaction?new_id={transaction.id}")
    except Exception:
        flash("Something went wrong.", "danger")

    return redirect("/simulateATransaction")


@app.route("/")
def home():
    allTransactions = Transaction.query.all()
    return render_template("index.html", allTransactions=allTransactions)

@app.route("/simulateATransaction", methods=["POST", "GET"])
def simulate_transaction():
    # Show only the latest 10 transactions (newest first) on the simulate page
    allTransactions = (
        Transaction.query.order_by(Transaction.date.desc()).limit(10).all()
    )
    flash_messages = get_flashed_messages(with_categories=True)
    # Pass through any new_id query param so the template can scroll/highlight
    new_id = request.args.get('new_id')
    return render_template(
        "index2.html",
        allTransactions=allTransactions,
        flash_messages=flash_messages,
        new_id=new_id,
    )


@app.route("/dashboard")
@app.route("/dashboard/<int:month>")
def dashboard1(month=None):
    curr_month = datetime.now().month
    curr_year = datetime.now().year
    if month is not None:
        curr_month = month

    # Build months dropdown up to the latest month that has transaction data for the current year.
    # If there are no transactions for the current year, fall back to current month.
    latest_tx_current_year = (
        Transaction.query.filter(db.extract('year', Transaction.date) == curr_year)
        .order_by(Transaction.date.desc())
        .first()
    )
    if latest_tx_current_year and getattr(latest_tx_current_year, 'date', None):
        latest_month_for_dropdown = latest_tx_current_year.date.month
    else:
        latest_month_for_dropdown = curr_month

    months = [
        {"num": i, "name": month_name[i]} for i in range(1, latest_month_for_dropdown + 1)
    ]

    search_query = request.args.get("q", "").strip()
    month_transaction_query = build_transaction_query(curr_month, curr_year)
    transaction_query = build_transaction_query(curr_month, curr_year, search_query)

    total_expense = (
        month_transaction_query.with_entities(db.func.sum(Transaction.amount)).scalar()
        or 0
    )
    total_transactions = month_transaction_query.count()
    top_category, top_category_amount = get_top_category_for_query(month_transaction_query)
    average_expense = total_expense / total_transactions if total_transactions else 0
    analytics = get_spending_analytics(month_transaction_query)

    category_data = (
        transaction_query.with_entities(
            Transaction.category, db.func.sum(Transaction.amount)
        )
        .group_by(Transaction.category)
        .all()
    )
    month_category_totals = get_category_totals_for_query(month_transaction_query)

    transactions = transaction_query.order_by(Transaction.date.desc()).all()
    filtered_total_expense = (
        transaction_query.with_entities(db.func.sum(Transaction.amount)).scalar() or 0
    )
    filtered_total_transactions = transaction_query.count()
    filtered_top_category, filtered_top_category_amount = get_top_category_for_query(
        transaction_query
    )
    # print("Analytics = ", analytics)
    
    prev_month, prev_year = get_previous_month(curr_month, curr_year)
    previous_month_transaction_query = build_transaction_query(prev_month, prev_year)
    previous_transaction_query = build_transaction_query(
        prev_month,
        prev_year,
        search_query,
    )
    previous_month_total_expense = (
        previous_month_transaction_query.with_entities(
            db.func.sum(Transaction.amount)
        ).scalar()
        or 0
    )
    prev_month_Transaction_amount = (
        previous_month_total_expense
    )
    filtered_previous_total_expense = (
        previous_transaction_query.with_entities(db.func.sum(Transaction.amount)).scalar()
        or 0
    )
    previous_total_transactions = previous_transaction_query.count()
    previous_top_category, _ = get_top_category_for_query(previous_transaction_query)
    previous_month_category_totals = get_category_totals_for_query(
        previous_month_transaction_query
    )

    # Compute lightweight signals from the already-loaded `transactions` list
    merchant_counts: dict[str, int] = {}
    merchant_amounts: dict[str, float] = {}
    weekend_spend = 0.0
    weekday_spend = 0.0

    for t in transactions:
        name = t.merchant_name or "N/A"
        amt = float(t.amount or 0)
        merchant_counts[name] = merchant_counts.get(name, 0) + 1
        merchant_amounts[name] = merchant_amounts.get(name, 0.0) + amt
        if getattr(t, "date", None) and getattr(t, "date").weekday() >= 5:
            weekend_spend += amt
        else:
            weekday_spend += amt

    month_merchant_counts: dict[str, int] = {}
    month_weekend_spend = 0.0
    month_transactions = month_transaction_query.order_by(Transaction.date.desc()).all()
    for t in month_transactions:
        name = t.merchant_name or "N/A"
        amt = float(t.amount or 0)
        month_merchant_counts[name] = month_merchant_counts.get(name, 0) + 1
        if getattr(t, "date", None) and getattr(t, "date").weekday() >= 5:
            month_weekend_spend += amt

    most_frequent_merchant_count = (
        max(month_merchant_counts.values()) if month_merchant_counts else 0
    )
    most_frequent_merchant_ratio = (
        (most_frequent_merchant_count / total_transactions) if total_transactions else 0
    )

    month_weekend_spending_ratio = (
        (month_weekend_spend / total_expense) if total_expense else 0
    )
    weekend_spending_ratio = (
        (weekend_spend / filtered_total_expense) if filtered_total_expense else 0
    )
    small_tx_count = sum(1 for t in transactions if float(t.amount or 0) < 100)
    small_tx_ratio = (
        (small_tx_count / filtered_total_transactions)
        if filtered_total_transactions
        else 0
    )
    largest_transaction = max(
        transactions,
        key=lambda transaction: float(transaction.amount or 0),
        default=None,
    )

    # Weekly spending totals for the selected month
    days_in_month = monthrange(curr_year, curr_month)[1]
    previous_days_in_month = monthrange(prev_year, prev_month)[1]
    number_of_weeks = (days_in_month + 6) // 7
    weekly_totals = [0.0] * number_of_weeks
    for t in transactions:
        if getattr(t, "date", None):
            day = getattr(t, "date").day
            week_index = min((day - 1) // 7, number_of_weeks - 1)
            weekly_totals[week_index] += float(t.amount or 0)

    weekly_labels = [f"Week {i + 1}" for i in range(number_of_weeks)]
    weekly_values = [round(value, 2) for value in weekly_totals]

    weekly_spending_data = [
        {
            "week": weekly_labels[i],
            "total": weekly_values[i],
            "range": f"{i*7+1}-{min((i+1)*7, days_in_month)}",
        }
        for i in range(number_of_weeks)
    ]

    insight_context = {
        "transactions": transactions,
        "total_expense": float(filtered_total_expense or 0),
        "total_transactions": filtered_total_transactions,
        "top_category": filtered_top_category,
        "top_category_amount": float(filtered_top_category_amount or 0),
        "merchant_counts": merchant_counts,
        "merchant_amounts": merchant_amounts,
        "largest_transaction": largest_transaction,
        "weekend_spending_ratio": weekend_spending_ratio,
        "small_tx_count": small_tx_count,
        "small_tx_ratio": small_tx_ratio,
        "calendar_avg_daily_spend": (float(filtered_total_expense or 0) / days_in_month),
    }
    key_insights = build_key_insights(insight_context)
    month_comparison_summary = build_month_comparison_summary(
        current_total_expense=float(filtered_total_expense or 0),
        current_total_transactions=filtered_total_transactions,
        current_top_category=filtered_top_category,
        current_days_in_month=days_in_month,
        previous_total_expense=float(filtered_previous_total_expense or 0),
        previous_total_transactions=previous_total_transactions,
        previous_top_category=previous_top_category,
        previous_days_in_month=previous_days_in_month,
    )

    financial_pulse = generate_financial_pulse(
        current_month_spending=total_expense,
        last_month_spending=prev_month_Transaction_amount,
        top_category=top_category,
        top_category_spending=top_category_amount,
        largest_transaction=analytics["largest_transaction"],
        total_transactions=total_transactions,
        most_frequent_merchant_count=most_frequent_merchant_count,
        most_frequent_merchant_ratio=most_frequent_merchant_ratio,
        weekend_spending_ratio=month_weekend_spending_ratio,
        avg_daily_spend=analytics.get("avg_daily_spend"),
    )
    financial_pulse_summary = build_financial_pulse_summary(
        financial_pulse=financial_pulse,
        current_total=float(total_expense or 0),
        previous_total=float(prev_month_Transaction_amount or 0),
        current_category_totals=month_category_totals,
        previous_category_totals=previous_month_category_totals,
    )


    # Split the query tuple results into distinct arrays
    labels = [row[0] for row in category_data]
    values = [float(row[1]) for row in category_data]

    trend_data = (
        db.session.query(
            db.func.strftime("%Y-%m", Transaction.date).label("month"),
            db.func.sum(Transaction.amount),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )


    # 2. Split the results into parallel arrays for JavaScript
    trend_labels = [row[0] for row in trend_data]  # e.g., ['2026-05', '2026-06']
    trend_values = [float(row[1]) for row in trend_data]  # e.g., [1520.0, 4680.0]

    curr_month_name = datetime(curr_year, curr_month, 1).strftime("%B")
    flash_messages = get_flashed_messages(with_categories=True)
    return render_template(
        "dashboard.html",
        total_expense=total_expense,
        total_transactions=total_transactions,
        month_spending=total_expense,
        top_category=top_category,
        average_expense=round(average_expense,2),
        chart_labels=labels,
        chart_values=values,
        transactions=transactions,
        search_query=search_query,
        curr_month=curr_month,
        curr_month_name=curr_month_name,
        trend_labels=trend_labels,
        trend_values=trend_values,
        analytics=analytics,
        financial_pulse=financial_pulse,
        financial_pulse_summary=financial_pulse_summary,
        prev_month_Transaction_amount = prev_month_Transaction_amount,
        key_insights=key_insights,
        month_comparison_summary=month_comparison_summary,
        weekly_labels=weekly_labels,
        weekly_values=weekly_values,
        weekly_spending_data=weekly_spending_data,
        flash_messages=flash_messages,
        months=months,
    )


@app.route("/delete/<int:id>", methods=["GET", "POST"])
def delete_transaction(id):
    next_url = request.args.get("next") or request.form.get("next") or "/simulateATransaction"
    if not next_url.startswith("/"):
        next_url = f"/{next_url}"

    transaction = Transaction.query.filter_by(id=id).first()
    if not transaction:
        flash("Unable to delete transaction.", "danger")
        return redirect(next_url)

    try:
        db.session.delete(transaction)
        db.session.commit()
        flash("Transaction deleted successfully.", "success")
    except Exception:
        flash("Unable to delete transaction.", "danger")

    return redirect(next_url)


@app.route("/update/<int:id>", methods=["GET", "POST"])
def update_transaction(id):
    next_url = request.args.get("next") or request.form.get("next") or "/simulateATransaction"
    if not next_url.startswith("/"):
        next_url = f"/{next_url}"

    transaction = Transaction.query.filter_by(id=id).first()
    if not transaction:
        flash("Unable to update transaction.", "danger")
        return redirect(next_url)

    if request.method == "POST":
        try:
            transaction.merchant_name = request.form.get("merchant_name")
            transaction.amount = float(request.form.get("amount"))
            transaction.notes = request.form.get("notes")
            transaction.payment_method = request.form.get("payment_method")
            transaction.category = categorize(transaction.merchant_name)

            db.session.commit()
            flash("Transaction updated successfully.", "success")
        except Exception:
            flash("Unable to update transaction.", "danger")
        return redirect(next_url)

    flash_messages = get_flashed_messages(with_categories=True)
    return render_template("update.html", transaction=transaction, next=next_url, flash_messages=flash_messages)


@app.route("/export/<int:month>")
def exportCSV(month=None):
    curr_month = month
    curr_year = datetime.now().year
    search_query = request.args.get("q", "").strip()

    arrayMonths = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    transaction_query = build_transaction_query(curr_month, curr_year, search_query)
    transactions = transaction_query.order_by(Transaction.date.desc()).all()

    total_transactions = len(transactions)
    total_amount = sum(t.amount for t in transactions)

    export_date = datetime.now().strftime("%d-%b-%Y")
    month_name = datetime(curr_year, curr_month, 1).strftime("%B")
    # Create CSV content

    csv_content = ""

    csv_content += "Smart Spend AI - Expense Report\n\n"

    csv_content += f"Export Date: {export_date}\n"
    csv_content += f"Month: {month_name}\n"

    csv_content += "Category: All Categories\n"

    csv_content += f"Search: {search_query if search_query else 'None'}\n"

    csv_content += f"Total Transactions: {total_transactions}\n"

    csv_content += f"Total Amount: ₹{total_amount:.2f}\n"

    csv_content += "-" * 60 + "\n\n"

    csv_content += "S.No,Date,Merchant Name,Category,Amount,Payment Method,Notes\n"
    for index, transaction in enumerate(transactions, start=1):
        csv_content += f"{index},{transaction.date},{transaction.merchant_name},{transaction.amount},{transaction.category},{transaction.payment_method},{transaction.notes}\n"

    # Create a response with the CSV content
    response = app.response_class(response=csv_content, status=200, mimetype="text/csv")
    response.headers["Content-Disposition"] = (
        f"attachment; filename=SmartSpend_{arrayMonths[curr_month - 1]}_{curr_year}_{search_query}.csv"
    )
    return response


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)
