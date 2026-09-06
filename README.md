<div align="center">

# Smart Spend AI

### Not just where your money goes — but what it means.

**A personalized financial intelligence companion for understanding spending behavior.**

Smart Spend AI turns raw transaction history into contextual categories, uncertainty-aware decisions, behavioral patterns, and financial insights.

</div>

---

## 🎯 What is Smart Spend AI?

Payment apps are very good at telling us **where money went**.

The harder question is:

> **What did that spending actually mean?**

Real-world Indian UPI and bank transactions are often messy. Merchant names can be abbreviated or unfamiliar, descriptions can be vague, and the same merchant can represent completely different kinds of spending.

Smart Spend AI is built to bridge that gap.

It combines **transaction context, semantic understanding, merchant signals, transaction amounts, historical behavior, and entity-level memory** to build a more useful picture of an individual's spending.

Instead of treating every transaction as an isolated record, the system asks:

- What was this transaction probably for?
- Does the context agree with the merchant?
- Have I seen similar behavior from this user before?
- How confident is the system?
- Should this transaction be categorized automatically, or should the user review it?

The long-term vision is a **Financial Intelligence Companion designed around the individual using it** — helping people understand their money today and eventually make better financial decisions before the money is gone.

---

## ✨ What makes it different?

Traditional expense trackers generally follow:

```text
Record → Categorize → Visualize
```

Smart Spend AI aims for:

```text
Understand → Reason → Remember → Detect Uncertainty → Analyze → Explain
```

### Context-aware categorization

A merchant name alone is not always enough.

For example:

> **Zomato + "engineering book purchase" → Education**

The system can use the transaction note and semantic context rather than blindly mapping Zomato to Food & Dining.

### Uncertainty and conflict detection

The system does not have to pretend it knows the answer.

For example:

> **Uber Ride + "monthly room rent" → Conflict / Needs Review**

When strong signals disagree, the transaction can be surfaced for user attention instead of being confidently misclassified.

### Personal historical memory

Past transactions can provide additional evidence for future decisions.

The system maintains merchant/entity-level history so repeated behavior can become increasingly personalized.

### Behavioral intelligence

Once transactions have meaningful categories, Smart Spend AI can explain changes in spending by looking at:

- Category changes
- Merchant drivers
- Transaction frequency
- Average transaction size
- New spending areas
- Distributed spending changes

This moves the product beyond a collection of charts toward **explanations of financial behavior**.

---

## 🧠 Intelligence Pipeline

The semantic layer uses a machine-learning text classifier, while the final transaction decision combines multiple sources of evidence.

```text
Transaction Note
      │
      ▼
Word TF-IDF (1–2 grams)
      +
Character TF-IDF (char_wb 3–5 grams)
      │
      ▼
Feature Union
      │
      ▼
Logistic Regression Classifier
      │
      ▼
Class Probabilities + Prediction Margin
      │
      ▼
Semantic Evidence / Abstention
      │
      ├──────────────┐
      ▼              ▼
Merchant &       Historical /
Context Signals  Entity Memory
      │              │
      └──────┬───────┘
             ▼
      Evidence + Confidence
             │
      ┌──────┴───────────┐
      ▼                  ▼
Categorized          Needs Review
                      / Conflict
```

The learned semantic model is **one evidence source**, not an unconditional decision-maker. Deterministic safeguards and contextual reasoning help the system handle ambiguous financial data safely.

---

## 🔍 Key Features

### Transaction Intelligence

- Context-aware transaction categorization
- Word + character TF-IDF semantic classification
- Merchant and contextual signals
- Amount-based evidence
- Historical transaction evidence
- Entity-level merchant memory
- Confidence and prediction-margin checks
- Conflict detection
- Unknown/abstention handling
- Attention queue for transactions requiring review

### Financial Analytics

- Monthly spending summaries
- Category-wise spending analysis
- Previous-month comparison
- Spending trends
- Transaction frequency analysis
- Average transaction/basket-size analysis
- Merchant-level spending changes
- New spending-area detection
- Behavioral spending insights

### Transaction Management

- Add transactions
- Edit transactions
- Delete transactions
- Search and filtering
- Category management
- CSV import/export
- Persistent transaction history

### User Experience

- Responsive fintech-style dashboard
- Light and dark mode
- Interactive Chart.js visualizations
- Toast notifications
- Clear attention/review states

---

## 🖼️ Product Preview

<p align="center">
  <img src="screenshots/landing.png" width="100%">
</p>

### Dashboard

<p align="center">
  <img src="screenshots/dashboard-Dark.png" width="100%">
</p>

### Analytics

<p align="center">
  <img src="screenshots/analytics-charts.png" width="100%">
</p>

### Transaction Management

<table>
<tr>
<td>
<img src="screenshots/update-transaction.png">
</td>
<td>
<img src="screenshots/simulate.png">
</td>
</tr>
</table>

### Light Mode

<p align="center">
  <img src="screenshots/light-dashboard.png" width="100%">
</p>

---

## 🏗️ System Architecture

```text
                         TRANSACTIONS
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
             Merchant      Context       Amount
                 │            │            │
                 └────────────┼────────────┘
                              ▼
                    Semantic Intelligence
                              │
                    Historical / Entity Memory
                              │
                    Evidence + Confidence
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
            Categorized               Needs Review
                 │                    / Conflict / Unknown
                 └────────────┬────────────┘
                              ▼
                     Financial Analytics
                              │
                              ▼
                    Behavioral Insights
```

### Application architecture

```text
Browser
   │
   ▼
Flask Web Application
   │
   ├── Transaction Management
   ├── Statement Import
   ├── Intelligence / Categorization
   ├── Financial Facts & Insights
   └── Dashboard / Analytics
          │
          ▼
     SQLAlchemy ORM
          │
          ▼
    SQLite Database
```

---

## 🛠 Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite |
| ORM | SQLAlchemy / Flask-SQLAlchemy |
| Semantic Classification | scikit-learn, TF-IDF, Logistic Regression |
| Data Processing | Pandas, NumPy |
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5 |
| Visualization | Chart.js |
| Testing | pytest |
| Deployment | Gunicorn / Render |

---

# 🚀 Quick Start

The repository contains a **pre-populated demo SQLite database**, so you can run the application locally and immediately explore the dashboard and transaction intelligence without importing your own data.

### 1. Clone the repository

```bash
git clone https://github.com/theanand108/smart_spend_AI.git
cd smart_spend_AI
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate it

**macOS / Linux**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Start the application

```bash
python app.py
```

### 6. Open the dashboard

Visit:

```text
http://127.0.0.1:5000
```

### Demo data

The repository includes a realistic demonstration dataset covering **January 2026 through September 5, 2026**. It contains contextual examples for semantic categorization, historical/entity memory, and transactions that intentionally require attention or review.

The data is synthetic/demo data and does not contain real financial information.

---

## 🧪 Running Tests

Install the dependencies first, then run:

```bash
pytest
```

The test suite covers transaction intelligence, semantic classification, historical/entity memory, attention handling, financial facts, and behavioral insight generation.

---

## 📂 Project Structure

```text
smart_spend_AI/
│
├── app.py
├── requirements.txt
├── requirements-ml.txt
├── README.md
├── PRODUCT_DESIGN_DOCUMENT.md
│
├── data/
│   ├── semantic_intent_dataset.csv
│   └── semantic_intent_augmentation_*.csv
│
├── instance/
│   └── smart_spend.db
│
├── src/
│   ├── intelligence/
│   │   ├── categorizer.py
│   │   ├── semantic_ml.py
│   │   ├── evidence.py
│   │   ├── context.py
│   │   ├── entity_memory.py
│   │   ├── attention.py
│   │   └── persistence.py
│   │
│   ├── analytics/
│   │   ├── financial_facts.py
│   │   └── insight_engine.py
│   │
│   └── ...
│
├── static/
│   ├── dashboard.js
│   ├── toast.js
│   ├── style.css
│   └── ...
│
├── templates/
│   ├── dashboard.html
│   ├── update.html
│   └── ...
│
├── screenshots/
└── tests/
```

---

## 🔄 How a Transaction Is Understood

A simplified example:

```text
"Zomato — engineering book purchase"
                    │
                    ▼
          Semantic understanding
                    │
                    ▼
          Education evidence
                    │
                    ├── Merchant signal: Food-related
                    ├── Note signal: Education-related
                    └── Context resolves disagreement
                    │
                    ▼
              Education
```

For an ambiguous transaction:

```text
"Uber Ride — monthly room rent"
                    │
                    ▼
          Conflicting evidence
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
     Uber → Travel      Note → Housing
          │                   │
          └─────────┬─────────┘
                    ▼
             Needs Review
```

The important design principle is that **uncertainty is a valid outcome**.

---

## 🗺️ Current State & Future Vision

### Built

- Context-aware transaction categorization
- Semantic text classification
- Merchant/context/amount evidence
- Historical and entity-level memory
- Confidence-aware decisions
- Conflict and uncertainty detection
- Attention queue
- Behavioral spending insights
- Financial analytics dashboard
- Transaction management
- CSV import/export
- Responsive UI with light/dark mode
- Automated test coverage

### Future direction

- Natural-language financial assistant
- Voice-based financial conversations
- Affordability and cash-flow forecasting
- Smarter budgeting assistance
- Personalized financial recommendations
- Bank/UPI integrations
- Multi-user accounts and cloud synchronization
- Mobile application

These are **future capabilities**, not claims about the current implementation.

---

## 💡 Product Philosophy

Smart Spend AI is built around a simple idea:

> **Payment platforms know where your money went. Financial intelligence should help you understand why.**

The product is designed to **assist rather than overwhelm**, to use personal history without requiring users to manually explain everything, and to surface uncertainty when the available evidence is not strong enough.

The broader product vision, design principles, and roadmap are documented in **PRODUCT_DESIGN_DOCUMENT.md**.

---

## 🤝 Contributing

Contributions, suggestions, and feedback are welcome.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License.

---

<div align="center">

⭐ If you find Smart Spend AI interesting, consider giving the repository a star.

Built with curiosity, product thinking, and a lot of late nights.

</div>
