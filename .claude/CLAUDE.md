# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
source venv/bin/activate
python app.py          # runs on http://localhost:5001
```

## Running tests

```bash
source venv/bin/activate
pytest                 # all tests
pytest tests/test_foo.py::test_name   # single test
```

## Architecture

**Spendly** is a Flask expense tracker built as a teaching scaffold. Students implement features step-by-step; several routes currently return placeholder strings.

### Entry point

`app.py` — all routes defined here. Runs on port 5001 with `debug=True`.

### Templates

`templates/base.html` is the shared shell (navbar + footer). All other templates extend it via `{% extends "base.html" %}` and use three blocks:
- `{% block content %}` — page body
- `{% block head %}` — per-page CSS/meta (loaded inside `<head>`)
- `{% block scripts %}` — per-page JS (loaded before `</body>`)

### Styling

`static/css/style.css` — global stylesheet with all CSS custom properties (`--ink`, `--accent`, `--paper`, `--font-display`, `--font-body`, etc.) defined in `:root`. All components use these variables.

`static/css/landing.css` — landing-page-only overrides, loaded via `{% block head %}` in `landing.html`. It overrides the `.hero` layout from a 2-column grid to a centered single-column flex column.

When adding per-page styles: create a new CSS file in `static/css/` and link it via `{% block head %}` in the relevant template, following the `landing.css` pattern.

### Database (not yet implemented)

`database/db.py` will expose three functions: `get_db()`, `init_db()`, `close_db()`. The database is SQLite; the `.db` / `.sqlite3` files are gitignored. Students implement this in Step 1.

### Placeholder routes

These routes in `app.py` return plain strings and are meant to be implemented by students: `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`.
