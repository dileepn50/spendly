# Spec: Registration

## Overview
This step adds account creation to Spendly. Currently `GET /register` only
renders the sign-up form (`templates/register.html`) — there is no handler
that actually creates a user. This step implements `POST /register`, which
validates the submitted form, hashes the password, inserts a new row into
the `users` table, starts a logged-in session for the new user, and
redirects them into the app. This is the foundation every later
session-dependent step (logout, profile, expenses) builds on.

## Depends on
Step 01 — Database setup (`users` table and `get_db()` must exist and work).

## Routes
- `POST /register` — validate name/email/password, create the user, start a session, redirect to `/profile` — public
- `GET /register` — unchanged, already implemented (renders the form)

No other new routes.

## Database changes
No database changes. The existing `users` table
(`id`, `name`, `email` UNIQUE, `password_hash`, `created_at`) already
supports registration as-is.

## Templates
- **Create:** none
- **Modify:** `templates/register.html` — repopulate the `name` and `email`
  inputs with previously submitted values (`value="{{ name or '' }}"`, etc.)
  when re-rendering after a validation error, so the user doesn't have to
  retype them.

## Files to change
- `app.py` — add `app.secret_key`; import `session`, `request`, `redirect`,
  `url_for`, `generate_password_hash`; change `/register` to accept
  `methods=["GET", "POST"]` and implement the POST branch.
- `templates/register.html` — repopulate `name`/`email` on validation error.

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.generate_password_hash` is already
installed and already used in `database/db.py`.

## Rules for implementation
- No SQLAlchemy or ORMs.
- Parameterised queries only.
- Passwords hashed with werkzeug (`generate_password_hash`, method
  `pbkdf2:sha256`, matching `database/db.py`'s existing convention).
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- Validate on the server even though the form has `required`/`type=email`
  HTML5 attributes (never trust client-side validation alone).
- Required validations for `POST /register`:
  - `name`, `email`, `password` all present and non-blank
  - `password` is at least 8 characters
  - `email` is not already registered (catch the `UNIQUE` constraint /
    pre-check with a `SELECT`) — show "Email already registered" and
    re-render the form with a 400-equivalent response (still `render_template`,
    no redirect)
- On success: insert the user, set `session["user_id"]` (and optionally
  `session["user_name"]`) to log them in immediately, then redirect to
  `/profile`.
- Do not implement `/login` or `/logout` logic in this step — those are
  separate, later steps in the roadmap.

## Definition of done
- [ ] `GET /register` still renders the form with no errors.
- [ ] Submitting valid name/email/password creates exactly one new row in
      `users` with a hashed (not plaintext) password.
- [ ] After successful registration, the browser is redirected to
      `/login` and the Flask session contains `user_id` for the new user.
- [ ] Submitting an email that already exists (e.g. `demo@spendly.com`)
      re-renders the registration page with an "Email already registered"
      error and does not create a duplicate row.
- [ ] Submitting a password under 8 characters re-renders the form with a
      validation error and does not create a row.
- [ ] Submitting with a blank required field re-renders the form with a
      validation error and does not create a row.
- [ ] Restarting the app (`python app.py`) still starts cleanly and the
      seeded demo user is unaffected.
