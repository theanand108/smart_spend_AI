from flask import render_template


def register_demo_dashboard(app):
    """Register the public, read-only product demo.

    This route intentionally has no database access, authentication state,
    transaction model access, or user-specific data.
    """

    @app.route("/demo")
    def demo_dashboard():
        return render_template(
            "demo_dashboard.html",
            demo_data={
                "month": "September 2026",
                "health": "Good",
                "summary": "Spending is under control this month, with most activity concentrated in everyday essentials.",
                "change": "+8%",
                "change_label": "Monthly spending increased",
                "current_total": "₹18,420",
                "previous_total": "₹17,060",
                "driver": "Food & Dining",
                "driver_change": "₹1,120 more",
                "driver_share": "82% of the monthly increase",
                "transactions": "42",
                "top_category": "Food & Dining",
                "average_day": "₹614",
            },
        )
