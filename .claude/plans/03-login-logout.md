# Implementation Plan: Login & Logout (`POST /login`, real `GET /logout`)

## Context

Registration (Step 02, merged) already creates users and establishes
`app.secret_key` / `flask.session` conventions in `app.py`, but `GET /login`
only renders the sign-in form with no handler that actually authenticates
anyone, and `GET /logout` is still a placeholder string
(`"Logout — coming in Step 3"`). Per `.claude/specs/03-login-logout.md`
(Step 3, branch `feature/login-logout`), this change adds `POST /login`
(verify credentials against the `users` table, start a session, redirect to
`/profile`) and turns `/logout` into a real route that clears the session
and redirects to `/`. This unblocks Step 04 (profile), which will need a
real logged-in session to know which user's data to show. Scope is
intentionally tight, mirroring the registration step: no login-required
guards on other routes yet (deferred to Step 04, since `/profile` is still
a placeholder), no Flask-Login, no CSRF, no rate limiting/lockout, no
session expiry.

Verified against the current repo (Explore agent, this session, post
registration-merge): `app.py` (146 lines) already has `session`,
`request`, `redirect`, `url_for` imported and `app.secret_key` set (from
Step 02); only `generate_password_hash` is imported from
`werkzeug.security` — `check_password_hash` is not yet imported. `/login`
is GET-only (`app.py:100-102`); `/logout` is the placeholder
(`app.py:119-121`). `templates/login.html` already has an `{% if error %}`
block wired but no `value=` repopulation on its email input (password
input correctly has none). `database/db.py`'s seeded demo user
(`demo@spendly.com` / `demo123`) is the concrete credential to test
against. All CSS classes needed (`.auth-error`, `.form-input`,
`.btn-submit`, `.auth-card`, `.auth-switch`) already exist — no new
styling needed.

## Changes

### 1. `app.py`

**Import** — add `check_password_hash` alongside the existing
`generate_password_hash` import:

```python
from werkzeug.security import generate_password_hash, check_password_hash
```

**Route** — replace the current GET-only `/login` (lines 100-102) with a
GET/POST handler that mirrors `/register`'s established conventions
exactly (`request.form.get(key, "").strip()`, `conn = get_db()` /
`try/finally: conn.close()`, `(render_template(...), 400)` for validation
failures, `session[...]` + `redirect(url_for(...))` on success):

```python
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

    return redirect(url_for("profile"))
```

Key decisions:
- Email is `.strip().lower()`'d before the lookup, matching how
  registration stores emails — so a login with `DEMO@SPENDLY.COM` still
  matches the stored `demo@spendly.com` row.
- `user is None or not check_password_hash(...)` is a single `if` with a
  short-circuited `or`, producing exactly one `render_template` call/error
  string/status code for both "no such user" and "wrong password" — this
  is deliberate: it must not be observably possible to tell from the
  response whether an email is registered. The `or` short-circuit also
  means `check_password_hash` is only called when `user is not None`,
  which is required (calling it on `None` would raise) and not a leak
  since it doesn't affect the response.
- Only `email` (never `password`) is passed back into the template for
  repopulation, matching the spec.
- Connection is opened, queried, and closed entirely within its own
  `try/finally` before any `session` mutation — same pattern as
  `/register`, no Flask `g`/teardown wiring (no precedent for that in this
  codebase).

**Route** — replace the `/logout` placeholder (lines 119-121) with:

```python
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))
```

`session.clear()` is safe even when no one is logged in: Flask always
provides a `session` dict-like object on every request (empty if there's
no cookie), and `dict.clear()` on an already-empty dict is a harmless
no-op — no defensive `if "user_id" in session` check is needed. `GET` is
implicit (no `methods=` needed), consistent with `/`, `/terms`, `/privacy`.
`url_for("landing")` resolves to `/`.

### 2. `templates/login.html`

One line added to the email input only (email input currently at lines
23-25; password input at lines 29-31 stays untouched — must never be
repopulated):

```html
<input type="email" id="email" name="email"
       class="form-input" placeholder="nitish@example.com"
       value="{{ email or '' }}"
       required autofocus>
```

The existing `{% if error %}<div class="auth-error">{{ error }}</div>{% endif %}`
block (lines 16-18) needs no changes — it already renders whatever `error`
string the route passes in.

## Out of scope (explicitly)

No login-required guards/decorators on `/profile` or any other route (Step
04's job once `/profile` is a real page), no Flask-Login, no CSRF token,
no rate limiting/lockout, no session expiry/"remember me", no database
schema changes.

## Verification

Run `source venv/bin/activate && python app.py` (port 5001; optionally
`rm spendly.db` first for a clean seed), then:

1. `curl -i http://127.0.0.1:5001/login` → 200, form HTML, empty
   `value=""` on email, no error banner.
2. Successful login with seeded demo credentials:
   `curl -i -c /tmp/cookies.txt -X POST http://127.0.0.1:5001/login -d "email=demo@spendly.com&password=demo123"`
   → `302` to `/profile`, `Set-Cookie` present. Then
   `curl -i -b /tmp/cookies.txt http://127.0.0.1:5001/profile` → 200
   (still the Step-4 placeholder string, unaffected by this step — just
   confirms the cookie carried through).
3. Wrong password: `email=demo@spendly.com&password=wrongpass` → `400`,
   "Invalid email or password.", email field still shows
   `demo@spendly.com`.
4. Nonexistent email: `email=nosuchuser@spendly.com&password=whatever` →
   `400`, same "Invalid email or password." message. Diff this response
   against step 3's (after normalizing the differing email value) to
   confirm the bodies are otherwise byte-identical — no user-enumeration
   leak.
5. Blank fields: `email=&password=` → `400`, "Email and password are
   required."
6. Case-insensitive email: `email=DEMO@SPENDLY.COM&password=demo123` →
   `302` to `/profile`, same as step 2.
7. Logout while logged in: reuse the cookie jar from step 2,
   `curl -i -b /tmp/cookies.txt -c /tmp/cookies.txt http://127.0.0.1:5001/logout`
   → `302` to `/`, with a `Set-Cookie` that clears/expires the session.
8. Logout while not logged in (fresh request, no cookie jar):
   `curl -i http://127.0.0.1:5001/logout` → `302` to `/`, no error/500.
9. Restart `python app.py` — starts cleanly (no import errors from the new
   `check_password_hash` import), demo login (step 2) still works after
   restart, confirming `seed_db()`'s idempotency is unaffected.
10. Browser pass: submit wrong credentials on `/login`, confirm the page
    re-renders in place with the `.auth-error` styling and the email field
    retained (password field empty); then log in successfully and confirm
    the address bar shows `/profile`; then visit `/logout` and confirm
    redirect to `/`.

## Post-implementation addition (not in original plan)

After implementing the above, a follow-up fix was applied: `templates/base.html`'s
navbar was static and always showed "Sign in" / "Get started" regardless of
session state. Fixed by conditionally rendering the navbar based on
`session.user_id` (Flask auto-injects `session` into the Jinja context):

```html
<div class="nav-links">
    {% if session.user_id %}
    <a href="{{ url_for('profile') }}">{{ session.user_name }}</a>
    <a href="{{ url_for('logout') }}" class="nav-cta">Log out</a>
    {% else %}
    <a href="{{ url_for('login') }}">Sign in</a>
    <a href="{{ url_for('register') }}" class="nav-cta">Get started</a>
    {% endif %}
</div>
```

Verified: logged-out navbar shows "Sign in"/"Get started"; after login the
navbar (on every page, since all templates extend `base.html`) shows the
user's name and "Log out"; after logout it reverts.
