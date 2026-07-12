import sqlite3

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)

# Dev-only placeholder — a real deployment must load this from an
# environment variable / secrets manager, never hardcode it.
app.secret_key = "dev-secret-key-change-in-production"

# ------------------------------------------------------------------ #
# Database setup — ensure schema exists and demo data is seeded       #
# before the app starts serving requests.                            #
# ------------------------------------------------------------------ #
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template(
            "register.html",
            error="All fields are required.",
            name=name,
            email=email,
        ), 400

    if len(password) < 8:
        return render_template(
            "register.html",
            error="Password must be at least 8 characters.",
            name=name,
            email=email,
        ), 400

    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing is not None:
            return render_template(
                "register.html",
                error="Email already registered.",
                name=name,
                email=email,
            ), 400

        password_hash = generate_password_hash(password, method="pbkdf2:sha256")
        try:
            cursor = conn.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (name, email, password_hash),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Race-condition backstop: another request registered this
            # email between our SELECT check and this INSERT.
            return render_template(
                "register.html",
                error="Email already registered.",
                name=name,
                email=email,
            ), 400

        user_id = cursor.lastrowid
    finally:
        conn.close()

    session["user_id"] = user_id
    session["user_name"] = name

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template(
            "login.html",
            error="Email and password are required.",
            email=email,
        ), 400

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html",
            error="Invalid email or password.",
            email=email,
        ), 400

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]

    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    display_name = session.get("user_name", "Demo User")
    parts = display_name.split()
    initials = (parts[0][0] + parts[1][0]).upper() if len(parts) >= 2 else display_name[:2].upper()

    user = {
        "name": display_name,
        "initials": initials,
        "email": "demo@spendly.com",
        "member_since": "March 2025",
    }

    stats = {
        "total_spent": 18240.00,
        "transaction_count": 34,
        "top_category": "Food",
    }

    transactions = [
        {"date": "Jul 10, 2026", "description": "Groceries at Trader Joe's", "category": "Food", "amount": 1432.00},
        {"date": "Jul 8, 2026", "description": "Uber ride to airport", "category": "Transport", "amount": 845.00},
        {"date": "Jul 5, 2026", "description": "Electricity bill", "category": "Bills", "amount": 2150.00},
        {"date": "Jul 3, 2026", "description": "Movie tickets", "category": "Entertainment", "amount": 960.00},
        {"date": "Jul 1, 2026", "description": "Dinner at Cafe Mocha", "category": "Food", "amount": 620.00},
    ]

    categories = [
        {"name": "Food", "amount": 6930.00, "percent": 38},
        {"name": "Bills", "amount": 5472.00, "percent": 30},
        {"name": "Transport", "amount": 3284.00, "percent": 18},
        {"name": "Entertainment", "amount": 2554.00, "percent": 14},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
