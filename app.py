from flask import Flask, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_spend.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    date = db.Column(db.DateTime, default = datetime.utcnow)
    merchant_name = db.Column(db.String, nullable = False)
    amount = db.Column(db.Float, nullable = False)
    category = db.Column(db.String(50), nullable = True)
    payment_method = db.Column(db.String(50))
    notes = db.Column(db.String(200))

    def __repr__(self):

        return f"<Transaction {self.merchant_name}>"

def categorize(merchant):
    merchant = str(merchant).lower()

    if "zomato" in merchant or "swiggy" in merchant or "starbucks" in merchant or "dominoz" in merchant:
        return "Food & Dining"
    elif "uber" in merchant or "ola" in merchant or "petrol" in merchant:
        return "Travel & Transport"
    elif "netflix" in merchant or "spotify" in merchant or "bookmyshow" in merchant:
        return "Entertainment"
    elif "blinkit" in merchant or "kirana" in merchant:
        return "Groceries"
    elif "airtel" in merchant:
        return "Bills & Utilities"
    elif "myntra" in merchant or "h&m" in merchant or "amazon" in merchant or "flipkart" in merchant:
        return "Shopping"
    elif "gym" in merchant:
        return "Health & Fitness"
    else:
        return "Others"
    
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
        payment_method=payment_method
    )

    db.session.add(transaction)
    db.session.commit()

    return redirect("/")

@app.route('/')
def home():
    allTransactions = Transaction.query.all()
    return render_template("index.html", allTransactions = allTransactions)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)
