"""Loads the question bank from the YAML files in content/."""

from pathlib import Path

import yaml

CONTENT_DIR = Path(__file__).parent / "content"


def load_bank():
    """Returns (topics, questions): a list of topics and a dict of questions by id."""
    topics = yaml.safe_load((CONTENT_DIR / "topics.yaml").read_text())["topics"]
    questions = {}

    for topic in topics:
        english = yaml.safe_load((CONTENT_DIR / "questions" / f"{topic['id']}.yaml").read_text())
        hebrew = yaml.safe_load((CONTENT_DIR / "he" / f"{topic['id']}.yaml").read_text())

        for q in english["questions"]:
            q["topic"] = topic["id"]
            q["he"] = hebrew["questions"].get(q["id"], {})
            questions[q["id"]] = q

    return topics, questions


def text(q, field, lang):
    """A field of a question in the chosen language (Hebrew falls back to English)."""
    if lang == "he" and field in q["he"]:
        return q["he"][field]
    if field == "keyPoints":
        return [kp["text"] for kp in q["rubric"]["keyPoints"]]
    return q.get(field)
