import sqlite3
from datetime import datetime

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

    user_id = session["user_id"]

    conn = get_db()
    try:
        user_row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()

        display_name = user_row["name"]
        parts = display_name.split()
        initials = (parts[0][0] + parts[1][0]).upper() if len(parts) >= 2 else display_name[:2].upper()
        member_since_dt = datetime.strptime(user_row["created_at"], "%Y-%m-%d %H:%M:%S")

        user = {
            "name": display_name,
            "initials": initials,
            "email": user_row["email"],
            "member_since": member_since_dt.strftime("%B %Y"),
        }

        # === SECTION: SUMMARY STATS (Subagent 2 — edit ONLY between these markers) ===
        totals_row = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_spent, COUNT(*) AS transaction_count
            FROM expenses WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        top_category_row = conn.execute(
            """
            SELECT category, SUM(amount) AS category_total
            FROM expenses WHERE user_id = ?
            GROUP BY category
            ORDER BY category_total DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        stats = {
            "total_spent": totals_row["total_spent"],
            "transaction_count": totals_row["transaction_count"],
            "top_category": top_category_row["category"] if top_category_row else "—",
        }
        # === END SECTION: SUMMARY STATS ===

        # === SECTION: TRANSACTION HISTORY (Subagent 1 — edit ONLY between these markers) ===
        tx_rows = conn.execute(
            """
            SELECT date, description, category, amount
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC, created_at DESC
            LIMIT 5
            """,
            (user_id,),
        ).fetchall()

        transactions = [
            {
                "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%b %-d, %Y"),
                "description": row["description"] or "",
                "category": row["category"],
                "amount": row["amount"],
            }
            for row in tx_rows
        ]
        # === END SECTION: TRANSACTION HISTORY ===

        # === SECTION: CATEGORY BREAKDOWN (Subagent 3 — edit ONLY between these markers) ===
        category_rows = conn.execute(
            """
            SELECT category, SUM(amount) AS amount
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY amount DESC
            """,
            (user_id,),
        ).fetchall()

        category_total = sum(row["amount"] for row in category_rows)

        categories = [
            {
                "name": row["category"],
                "amount": row["amount"],
                "percent": round(row["amount"] / category_total * 100) if category_total > 0 else 0,
            }
            for row in category_rows
        ]
        # === END SECTION: CATEGORY BREAKDOWN ===
    finally:
        conn.close()

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
