# Spec: Login Logout

## Overview
This step adds session-based sign-in and sign-out to Spendly. Registration
(Step 02) already creates users and establishes `app.secret_key` /
`flask.session` conventions, but `GET /login` only renders the sign-in form
with no handler that actually authenticates anyone, and `GET /logout` is
still a placeholder string (`"Logout — coming in Step 3"`). This step
implements `POST /login` (verify credentials against the `users` table,
start a session) and turns `/logout` into a real route that clears the
session. This unblocks Step 04 (profile), which will need a real logged-in
session to know which user's data to show.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`).
- Step 02 — Registration (`app.secret_key` already set in `app.py`; users
  exist with `password_hash` created via
  `generate_password_hash(password, method="pbkdf2:sha256")`; emails are
  stored lowercased).

## Routes
- `POST /login` — validate email/password against `users`, start a session, redirect to `/profile` — public
- `GET /login` — unchanged, already implemented (renders the form)
- `GET /logout` — clear the session, redirect to `/` — currently a placeholder returning plain text; replaced with real logic. Public (no-op safely even if no one is logged in).

No other new routes. Route-protection (redirecting anonymous users away
from `/profile` or other logged-in-only pages) is **not** part of this
step — that belongs to Step 04, once `/profile` is a real page instead of
a placeholder string.

## Database changes
No database changes. The existing `users` table
(`id`, `name`, `email` UNIQUE, `password_hash`, `created_at`) already
supports login as-is.

## Templates
- **Create:** none
- **Modify:** `templates/login.html` — repopulate the `email` input
  (`value="{{ email or '' }}"`) when re-rendering after a failed login,
  matching the pattern already used in `templates/register.html`. Password
  is never repopulated.

## Files to change
- `app.py` — import `check_password_hash` from `werkzeug.security`; change
  `/login` to accept `methods=["GET", "POST"]` and implement the POST
  branch; replace the `/logout` placeholder with real session-clearing
  logic.
- `templates/login.html` — repopulate `email` on validation error.

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` ships
alongside `generate_password_hash`, already installed and already used in
`database/db.py` / `app.py`.

## Rules for implementation
- No SQLAlchemy or ORMs.
- Parameterised queries only.
- Passwords verified with werkzeug's `check_password_hash` (never compare
  plaintext, never re-hash and compare hashes manually).
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- Validate on the server even though the form has `required`/`type=email`
  HTML5 attributes.
- Required behavior for `POST /login`:
  - `email`, `password` both present and non-blank — if not, "Email and
    password are required."
  - Normalize the submitted email the same way registration does
    (`.strip().lower()`) before looking it up, so casing matches what was
    stored.
  - Look up the user by email; if no user matches OR
    `check_password_hash(user["password_hash"], password)` is `False`,
    show a single generic message: "Invalid email or password." — do not
    reveal whether the email exists (no user enumeration) — re-render the
    form with a 400-equivalent response (`render_template(...), 400`, no
    redirect), repopulating only `email`.
- On success: set `session["user_id"]` and `session["user_name"]` to the
  matched user's id/name, then redirect to `/profile`.
- `GET /logout`: call `session.clear()` and redirect to `/` (the landing
  page). Must not error if there was no active session.
- Do not add login-required guards/decorators to `/profile` or any other
  route in this step — that's Step 04's job once `/profile` stops being a
  placeholder.

## Definition of done
- [ ] `GET /login` still renders the form with no errors.
- [ ] `POST /login` with the seeded demo credentials
      (`demo@spendly.com` / `demo123`) redirects to `/profile` and the
      Flask session contains `user_id` for the demo user.
- [ ] `POST /login` with a correct email but wrong password shows
      "Invalid email or password.", no session is set, and no `user_id`
      cookie is issued.
- [ ] `POST /login` with an email that has no matching account shows the
      same "Invalid email or password." message (not a different one) —
      confirms no user enumeration.
- [ ] `POST /login` with a blank email or password shows "Email and
      password are required." and does not attempt a DB lookup.
- [ ] Logging in with an email in a different case than it was registered
      with (e.g. `DEMO@SPENDLY.COM`) still succeeds.
- [ ] `GET /logout` after being logged in clears the session (a subsequent
      request no longer carries a valid `user_id` in session) and redirects
      to `/`.
- [ ] `GET /logout` when not logged in does not error — it simply redirects
      to `/`.
- [ ] Restarting the app (`python app.py`) still starts cleanly and
      existing registration/seed behavior is unaffected.
