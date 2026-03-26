# balatro_save_editor

Balatro save editor with 3 interfaces over one shared backend:

- CLI: `main.py`
- Desktop GUI (PyQt6): `gui.py`
- Web app (Flask): `web.py`

The project keeps the save format intact (compressed Lua-like table text inside `.jkr`) and edits data through parser-based transforms.

## Features

- Economy and round stats editing (money, chips, hands/discards, reroll, blind target)
- Card area editing (`deck`, `hand`, `jokers`, `consumeables`)
- Joker add/remove and card modifier editing (edition, seal, stickers)
- Scoped apply (`selected`, `same_id`, `all`) in Card Properties
- Backup, restore, and undo
- Save validation before write

## Project Structure

- `core/`: parser/editor/validation logic
- `services/`: service layer used by CLI/GUI/Web
- `ui/`: PyQt6 interface
- `webapp/`: Flask routes + static web UI
- `utils/`: input helpers for CLI

## Dependencies

- Python 3.10+
- Web mode: `Flask`
- GUI mode: `PyQt6`
- Optional CLI colors: `colorama`

Install example:

```bash
pip install flask pyqt6 colorama
```

## Run

### CLI

```bash
python main.py
```

### Desktop GUI

```bash
python gui.py
```

### Web

```bash
python web.py
```

Open `http://127.0.0.1:5000`.

For Render production deploy, do not run Flask development server (`python web.py`).
Use Gunicorn as Start Command:

```bash
gunicorn web:app --bind 0.0.0.0:${PORT:-10000} --workers ${WEB_CONCURRENCY:-1}
```

This repository includes a `render.yaml` blueprint with this configuration.

If your Render service was created manually before adding `render.yaml`, update the service Start Command in Render dashboard to the command above.

## Balatro-Core Integration

The editor supports data-driven mapping from extracted game source (`Balatro-Core/*.lua`) when the folder is present locally.

`Balatro-Core/` is intentionally git-ignored because it is external game data.

## Git Notes

- `Balatro-Core/` is ignored in `.gitignore`
- local caches (`__pycache__`, `*.pyc`) are ignored
