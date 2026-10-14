from ysr.models import Question

SCALE_LABELS = {
    0: "Doğru değil",
    1: "Biraz ya da bazen doğru",
    2: "Çok ya da sık sık doğru",
}
RATING_NAMES = {
    "time": "Zaman",
    "skill": "Başarı",
    "active": "Aktiflik",
    "grade": "Başarı",
}


def _choice_label(choices, value):
    for choice in choices:
        if choice["value"] == value:
            return choice["label"]
    return str(value)


def _activity_lines(question, data):
    if not data:
        return []
    if data.get("none"):
        return ["Hiçbiri"]
    ratings = question.options["ratings"]
    lines = []
    for item in data.get("items", []):
        parts = [
            f'{RATING_NAMES.get(r["key"], r["key"])}: {_choice_label(r["choices"], item.get(r["key"]))}'
            for r in ratings
        ]
        lines.append(f'{item["name"]} — ' + "; ".join(parts))
    return lines


def _answer_lines(question, answer):
    qtype = question.question_type
    if qtype == Question.Type.SCALE_012:
        return [f"{answer.value} – {SCALE_LABELS.get(answer.value, '')}"]
    if qtype == Question.Type.SINGLE_CHOICE:
        return [_choice_label(question.options, answer.value)]
    if qtype == Question.Type.FREE_TEXT:
        return [answer.text]
    if qtype == Question.Type.ACTIVITY_LIST:
        return _activity_lines(question, answer.data)
    return []


def build_report(session):
    """Oturumdaki tüm soruları sırayla, verilen cevaplarla birlikte döndürür."""
    answers = {a.question_id: a for a in session.answers.all()}
    rows = []
    for question in Question.objects.select_related("section"):
        answer = answers.get(question.id)
        row = {
            "code": question.code,
            "text": question.text,
            "section": question.section.title,
            "is_header": question.is_header,
            "depth": 1 if question.parent_id else 0,
            "answered": answer is not None,
            "lines": [],
            "explanation": "",
            "critical": False,
        }
        if answer:
            row["lines"] = _answer_lines(question, answer)
            if question.question_type != Question.Type.FREE_TEXT:
                row["explanation"] = answer.text
            row["critical"] = bool(
                question.is_critical and answer.value and answer.value > 0
            )

        classes = []
        if row["critical"]:
            classes.append("critical")
        if row["depth"]:
            classes.append("child")
        if row["is_header"]:
            classes.append("header")
        row["css"] = " ".join(classes)
        row["answer"] = "\n".join(row["lines"])
        rows.append(row)

    return {
        "rows": rows,
        "critical": [r for r in rows if r["critical"]],
    }
