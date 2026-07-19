# Spec: Backend Routes for Profile Page

## Overview
Step 4 built the `/profile` page UI against hardcoded Python dicts so the
design could be validated before any real queries existed. This step
replaces that hardcoded data with real SQL queries against the `users` and
`expenses` tables, scoped to the logged-in user (`session["user_id"]`).
The route, template, and auth guard already exist — this step only changes
where the data passed to `profile.html` comes from. This is the last piece
needed before expense CRUD (Steps 7–9) can be meaningfully tested against
real data.

## Depends on
- Step 01 — Database setup (`users`, `expenses` tables; `get_db()`).
- Step 02 — Registration (users can exist with real accounts, not just the
  seeded demo user).
- Step 03 — Login/Logout (`session["user_id"]` is set on login).
- Step 04 — Profile page (`/profile` route, auth guard, and
  `templates/profile.html` already render the four sections this step now
  feeds with real data).

## Routes
No new routes. `GET /profile` is modified in place:
- `GET /profile` — render the profile page using real data queried for
  `session["user_id"]` — logged-in only (unchanged: redirect to `/login` if
  no `user_id` in session).

## Database changes
No database changes. The existing `users` and `expenses` tables
(`id`, `user_id`, `amount`, `category`, `date`, `description`,
`created_at`) are sufficient for every value currently shown on the page.

## Queries needed in `GET /profile`
All queries are parameterised and scoped to `user_id = session["user_id"]`.

- **User info** — `name`, `email` from `users` where `id = user_id`.
  `member_since` derived from `users.created_at`. Avatar initials computed
  from `name`, same logic as the current placeholder.
- **Summary stats** — `total_spent` = `SUM(amount)` from `expenses` for the
  user; `transaction_count` = `COUNT(*)`; `top_category` = the category
  with the highest `SUM(amount)` (`GROUP BY category ORDER BY SUM(amount)
  DESC LIMIT 1`). If the user has no expenses, all three default to `0` /
  `"—"` rather than erroring.
- **Transaction history** — most recent expenses for the user (`ORDER BY
  date DESC, created_at DESC`), limited to a fixed page size (5, matching
  the current hardcoded example) — `date`, `description`, `category`,
  `amount`.
- **Category breakdown** — per-category `SUM(amount)` for the user,
  `GROUP BY category ORDER BY SUM(amount) DESC`, with `percent` computed
  in Python as `(category_total / total_spent) * 100` rounded to the
  nearest whole number (guard against division by zero when
  `total_spent` is 0).

## Templates
- **Create:** none
- **Modify:** `templates/profile.html` — add an empty-state message (e.g.
  "No expenses yet — add your first one to see it here") in the
  transaction history and category breakdown sections when the user has
  zero expenses, so the page doesn't render broken/empty tables. Category
  badge CSS classes and layout stay as already implemented in Step 04.

## Files to change
- `app.py` — replace the hardcoded `user`, `stats`, `transactions`, and
  `categories` dicts/lists in the `/profile` view with real queries via
  `get_db()`.
- `templates/profile.html` — add empty-state handling for zero-expense
  users.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()`.
- Parameterised queries only — never string-format SQL, especially the
  `user_id` filter.
- Passwords hashed with werkzeug — unchanged in this step (no auth logic
  touched).
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- Every query must filter by `user_id = session["user_id"]` — a user must
  never see another user's expenses, stats, or transaction history.
- Format currency as INR (₹), matching the existing hardcoded values in
  `profile.html`/`profile.css` — do not switch to `$` or any other symbol.
- Close every DB connection (`conn.close()` in a `finally` block, matching
  the existing pattern in `/register` and `/login`).
- Handle the zero-expenses case explicitly in Python (don't let `SUM()`
  returning `NULL` or a percent division by zero reach the template).

## Definition of done
- [ ] Visiting `/profile` without being logged in still redirects to
      `/login` (unchanged from Step 04).
- [ ] Logging in as the seeded demo user (`demo@spendly.com` / `demo123`)
      and visiting `/profile` shows the 8 seeded expenses' real total,
      count, and top category — not the old hardcoded values.
- [ ] The transaction history table shows real rows from the `expenses`
      table for the logged-in user, most recent first.
- [ ] The category breakdown shows real per-category totals and
      percentages that sum to ~100%.
- [ ] Registering a brand-new user and visiting `/profile` immediately
      after shows a correct empty state (₹0 total, 0 transactions, no
      broken tables) instead of an error or leftover hardcoded data.
- [ ] A second logged-in user never sees the demo user's (or any other
      user's) expenses on their own `/profile` page.
- [ ] No hex colour values appear in any modified template — only CSS
      variables.
- [ ] Restarting the app (`python app.py`) still starts cleanly and
      existing registration/login/seed behavior is unaffected.
