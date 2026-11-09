"""DevOps Ready: practice questions for junior DevOps interviews."""

import html
import random
import re

import markdown
from flask import Flask, abort, redirect, render_template, request, url_for
from markupsafe import Markup

import db
import grading
from content import load_bank, text

app = Flask(__name__)
TOPICS, QUESTIONS = load_bank()
TOPICS_BY_ID = {t["id"]: t for t in TOPICS}
db.init()

# Interface text in both languages.
UI = {
    "en": {
        "title": "DevOps Ready", "home": "Topics", "review": "Mistakes", "switch": "עברית",
        "answered": "answered", "correct_count": "correct", "start": "Practice",
        "check": "Check", "show_answer": "Show the answer", "next": "Next question", "back": "Back to topics",
        "your_command": "Your command", "your_answer": "Your answer (optional)",
        "order_help": "Give each step its position (1 = first).", "order_error": "Use each number once.",
        "score": "Score", "correct": "Correct", "partial": "Partly correct", "incorrect": "Not correct",
        "right_answer": "The right answer", "model_answer": "Model answer", "explanation": "Why",
        "self_check": "Which of these points did you cover?", "save_self": "Save my score",
        "no_mistakes": "No mistakes to review. Nice!", "review_help": "Questions where your last answer was not correct.",
        "level": "Level",
    },
    "he": {
        "title": "DevOps Ready", "home": "נושששששששששאים", "review": "טעויות", "switch": "English",
        "answered": "נענו", "correct_count": "נכונות", "start": "תרגול",
        "check": "בדיקה", "show_answer": "הצגת התשובה", "next": "לשאלה הבאה", "back": "חזרה לנושאים",
        "your_command": "הפקודה שלכם", "your_answer": "התשובה שלכם (לא חובה)",
        "order_help": "תנו לכל שלב את המקום שלו (1 = ראשון).", "order_error": "כל מספר צריך להופיע פעם אחת.",
        "score": "ציון", "correct": "נכון", "partial": "נכון חלקית", "incorrect": "לא נכון",
        "right_answer": "התשובה הנכונה", "model_answer": "תשובה לדוגמה", "explanation": "הסבר",
        "self_check": "אילו מהנקודות האלה כיסיתם?", "save_self": "שמירת הציון",
        "no_mistakes": "אין טעויות לחזור עליהן. כל הכבוד!", "review_help": "שאלות שהתשובה האחרונה שלכם בהן לא הייתה נכונה.",
        "level": "רמה",
    },
}


# ---------- Helpers available in the templates ----------

def get_lang():
    return request.cookies.get("lang", "he")


@app.context_processor
def template_helpers():
    lang = get_lang()
    return {
        "lang": lang,
        "t": UI[lang],
        "tx": lambda q, field: text(q, field, lang),
        "topic_title": lambda topic: topic["he"] if lang == "he" else topic["title"],
    }


LIST_ITEM = re.compile(r"\s*([-*]|\d+\.)\s")


def to_html(value, inline=False):
    """Markdown to HTML. Text outside `code` is escaped first, so '<pod>' stays visible."""
    parts = str(value).split("`")
    for i in range(0, len(parts), 2):
        parts[i] = html.escape(parts[i], quote=False)

    # Markdown needs an empty line before and after a list; the content doesn't always have one.
    lines = []
    for line in "`".join(parts).split("\n"):
        if lines and lines[-1].strip() and line.strip() and bool(LIST_ITEM.match(line)) != bool(LIST_ITEM.match(lines[-1])):
            lines.append("")
        lines.append(line)

    result = markdown.markdown("\n".join(lines), extensions=["nl2br", "sane_lists"])
    if inline:
        result = re.sub(r"^<p>(.*)</p>$", r"\1", result, flags=re.S)
    return Markup(result)


app.jinja_env.filters["md"] = to_html
app.jinja_env.filters["md_inline"] = lambda value: to_html(value, inline=True)


# ---------- Pages ----------

@app.route("/")
def index():
    scores = db.latest_scores()
    rows = []
    for topic in TOPICS:
        ids = [q["id"] for q in QUESTIONS.values() if q["topic"] == topic["id"]]
        rows.append({
            "topic": topic,
            "total": len(ids),
            "answered": sum(1 for i in ids if i in scores),
            "correct": sum(1 for i in ids if scores.get(i, 0) >= 85),
        })
    return render_template("index.html", rows=rows)


@app.route("/topic/<topic_id>")
def practice_topic(topic_id):
    """Picks the next question: new ones first, then ones answered wrong, then any."""
    if topic_id not in TOPICS_BY_ID:
        abort(404)
    scores = db.latest_scores()
    questions = [q for q in QUESTIONS.values() if q["topic"] == topic_id]
    new = [q for q in questions if q["id"] not in scores]
    wrong = [q for q in questions if scores.get(q["id"], 100) < 85]
    question = random.choice(new or wrong or questions)
    return redirect(url_for("question", question_id=question["id"]))


@app.route("/question/<question_id>", methods=["GET", "POST"])
def question(question_id):
    q = QUESTIONS.get(question_id) or abort(404)
    page = {"q": q, "topic": TOPICS_BY_ID[q["topic"]], "result": None, "error": None, "revealed": False}

    # Options and steps are shown shuffled; the form sends back their original index.
    if q["type"] == "mcq":
        page["option_order"] = random.sample(range(len(q["options"])), len(q["options"]))
    if q["type"] == "order":
        page["step_order"] = random.sample(range(len(q["steps"])), len(q["steps"]))

    if request.method == "GET":
        return render_template("question.html", **page)

    form = request.form
    score = None

    if q["type"] == "mcq":
        page["picked"] = [int(i) for i in form.getlist("option")]
        score = grading.grade_mcq(q, page["picked"])

    elif q["type"] == "command":
        page["answer"] = form.get("answer", "")
        score = grading.grade_command(q, page["answer"])

    elif q["type"] == "order":
        positions = {i: form.get(f"pos_{i}", "") for i in range(len(q["steps"]))}
        if sorted(positions.values()) != [str(n) for n in range(1, len(q["steps"]) + 1)]:
            page["error"] = True
            return render_template("question.html", **page)
        order = sorted(positions, key=lambda i: int(positions[i]))
        page["user_order"] = order
        score = grading.grade_order(q, order)

    elif q["type"] == "open":
        page["answer"] = form.get("answer", "")
        page["revealed"] = True
        if form.get("action") == "selfgrade":
            score = grading.grade_self(q, [int(i) for i in form.getlist("kp")])
        else:
            return render_template("question.html", **page)

    db.save_attempt(q["id"], q["topic"], score)
    page["result"] = {"score": score, "verdict": grading.verdict(score)}
    return render_template("question.html", **page)


@app.route("/review")
def review():
    scores = db.latest_scores()
    mistakes = [QUESTIONS[i] for i, score in scores.items() if score < 85 and i in QUESTIONS]
    return render_template("review.html", mistakes=mistakes)


@app.route("/lang")
def switch_language():
    response = redirect(request.referrer or url_for("index"))
    response.set_cookie("lang", "en" if get_lang() == "he" else "he", max_age=60 * 60 * 24 * 365)
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5001)
