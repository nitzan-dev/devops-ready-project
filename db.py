"""Saves answers in a SQLite file (one table, one user)."""

import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "progress.db")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS attempts (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   question_id TEXT NOT NULL,
                   topic TEXT NOT NULL,
                   score INTEGER NOT NULL,
                   created_at TEXT DEFAULT CURRENT_TIMESTAMP
               )"""
        )


def save_attempt(question_id, topic, score):
    with connect() as conn:
        conn.execute("INSERT INTO attempts (question_id, topic, score) VALUES (?, ?, ?)", (question_id, topic, score))


def latest_scores():
    """{question_id: score of the most recent attempt}."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT question_id, score FROM attempts
               WHERE id IN (SELECT MAX(id) FROM attempts GROUP BY question_id)"""
        ).fetchall()
    return {row["question_id"]: row["score"] for row in rows}
