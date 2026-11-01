# DevOps Ready (Python)

A small Flask app for practicing junior DevOps interview questions, in Hebrew and English.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Open http://localhost:5001

Progress is saved in `progress.db` (SQLite). Set `DB_PATH` to store it somewhere else.

## Files

| File | What it does |
|---|---|
| `app.py` | The Flask app: pages, routes and interface text |
| `content.py` | Loads the questions from `content/` |
| `grading.py` | Grades answers (multiple choice, commands, order, self-check) |
| `db.py` | Saves answers in SQLite |
| `templates/` | The HTML pages (Jinja2) |
| `static/style.css` | The design |
| `content/` | 507 questions: `questions/` in English, `he/` in Hebrew, `topics.yaml` |
