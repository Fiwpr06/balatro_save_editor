# Balatro Save Editor

Balatro save editor with shared core logic and a web-first entrypoint:

- Web app (Flask): `main.py`

The project preserves the `.jkr` save format (compressed Lua-like table text) and applies parser-based transforms instead of destructive rewrites.

## Web Modes

After starting `python main.py`, you get:

- Save Mode: `http://127.0.0.1:5000/`
- Collection & Profile Mode: `http://127.0.0.1:5000/collection-editor`

## Features

### Save Mode

- Resource and capacity editing (money, chips, reroll cost, hands/discards, slot limits)
- Card area editing for `deck`, `hand`, `jokers`, and `consumeables`
- Joker/Card editing with scoped apply (`selected`, `same_id`, `all`)
- Voucher tools (catalog, unlock selected, unlock all)
- Consumable tools (Tarot/Planet/Spectral pool, add selected, refresh current)
- God actions and utility actions
- Backup history, restore backup, and undo last in-memory change
- Save validation before write/download

### Collection & Profile Mode

- Collection state editor (unlock/discover/alert flow)
- Import/export `.jkr` directly in browser
- Profile editor for high scores, career stats, progress, deck usage, joker/consumable usage
- Mobile-friendly sidebar and category navigation

### Data Fidelity

- Uses `Balatro-Core` metadata and texture atlas mapping for render payloads
- Planet/Spectral consumables are resolved with Tarot atlas (`Tarots.png`) to match Balatro core behavior

## Requirements

- Python 3.10+ (3.11 recommended)
- Dependencies in `requirements.txt`:
  - `Flask`
  - `gunicorn` (production)

Install:

```bash
pip install -r requirements.txt
```

## Run

### Web (Local)

```bash
python main.py
```

Open:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/collection-editor`

### Web (Render / Production)

Do not use Flask development server in production. Use Gunicorn:

```bash
gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --workers ${WEB_CONCURRENCY:-1}
```

`render.yaml` already contains this setup.

## Balatro-Core Requirement

`Balatro-Core/` is required for web runtime because upload/session initialization and render asset mapping depend on game data.

If this directory is missing in deployment, upload will fail with a server-side error.

## Project Structure

- `core/`: parser/editor/validation and core catalog logic
- `services/`: service layer used by Web
- `webapp/`: Flask routes, templates, and static assets
  - `templates/index.html`: Save Mode UI
  - `templates/collection_editor.html`: Collection/Profile UI
  - `static/collection-editor/`: collection/profile frontend bundle
- `ui/`: reserved legacy UI folder (no active desktop launcher)

## Git Notes

- Python caches are ignored (`__pycache__`, `*.pyc`)
- virtual env folders are ignored (`.venv/`, `venv/`)
- editor/OS temp files are ignored (`.vscode/`, `.DS_Store`, `Thumbs.db`)
