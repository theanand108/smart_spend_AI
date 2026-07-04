from calendar import month

# pyright: reportMissingImports=false
from flask import Flask, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from datetime import datetime

app = Flask(__name__)

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

@app.route("/submit_expense", methods=["POST"])
def submit():
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

    return redirect("/simulateATransaction")


@app.route("/")
def home():
    allTransactions = Transaction.query.all()
    return render_template("index.html", allTransactions=allTransactions)

@app.route("/simulateATransaction", methods=["POST", "GET"])
def simulate_transaction():
    allTransactions = Transaction.query.all()
    return render_template("index2.html", allTransactions=allTransactions)


@app.route("/dashboard")
@app.route("/dashboard/<int:month>")
def dashboard1(month=None):
    curr_month = datetime.now().month
    curr_year = datetime.now().year
    if month is not None:
        curr_month = month

    search_query = request.args.get("q", "").strip()
    transaction_query = build_transaction_query(curr_month, curr_year, search_query)

    total_expense = (
        transaction_query.with_entities(db.func.sum(Transaction.amount)).scalar() or 0
    )
    total_transactions = transaction_query.count()
    top_category_query = (
        transaction_query.with_entities(
            Transaction.category, db.func.sum(Transaction.amount).label("total")
        )
        .group_by(Transaction.category)
        .order_by(db.text("total DESC"))
        .first()
    )

    top_category = top_category_query[0] if top_category_query else "N/A"
    average_expense = total_expense / total_transactions if total_transactions else 0

    category_data = (
        transaction_query.with_entities(
            Transaction.category, db.func.sum(Transaction.amount)
        )
        .group_by(Transaction.category)
        .all()
    )

    transactions = transaction_query.order_by(Transaction.date.desc()).all()
    analytics = get_spending_analytics(transaction_query)
    # print("Analytics = ", analytics)
    
    prev_month_Transaction_amount = (
        db.session.query(db.func.sum(Transaction.amount))
        .filter(
            db.extract("month", Transaction.date) == (curr_month - 1),
            db.extract("year", Transaction.date) == curr_year,
        )
        .scalar()
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
        prev_month_Transaction_amount = prev_month_Transaction_amount

    )


@app.route("/delete/<int:id>", methods=["GET", "POST"])
def delete_transaction(id):
    transaction = Transaction.query.filter_by(id=id).first()
    db.session.delete(transaction)
    db.session.commit()
    return redirect("/simulateATransaction")


@app.route("/update/<int:id>", methods=["GET", "POST"])
def update_transaction(id):
    transaction = Transaction.query.filter_by(id=id).first()
    if request.method == "POST":
        transaction.merchant_name = request.form.get("merchant_name")
        transaction.amount = float(request.form.get("amount"))
        transaction.notes = request.form.get("notes")
        transaction.payment_method = request.form.get("payment_method")
        transaction.category = categorize(transaction.merchant_name)

        db.session.commit()
        return redirect("/simulateATransaction")
    return render_template("update.html", transaction=transaction)


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
