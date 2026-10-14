from rest_framework.exceptions import ValidationError

from ysr.models import Answer, Question

from . import answers as answer_service

Type = Question.Type

KINDS = {
    Type.SCALE_012: "scale",
    Type.SINGLE_CHOICE: "choice",
    Type.FREE_TEXT: "text",
    Type.ACTIVITY_LIST: "list",
}
MAX_TEXT = 2000
MSG_INVALID = "Bu cevap geçerli görünmüyor. Lütfen tekrar dene."
MSG_LIST = "Yazdığın her satır için bütün seçenekleri işaretle."
MSG_MISSING = "Bu soruyu cevaplamayı unutma."


def _prefix(question):
    return f"q{question.id}"


def _to_int(raw):
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _rows_from_post(question, post):
    prefix = _prefix(question)
    config = question.options
    rows = []
    for i in range(config["max_items"]):
        row = {"name": post.get(f"{prefix}_name{i}", "").strip()}
        for rating in config["ratings"]:
            row[rating["key"]] = post.get(f"{prefix}_{rating['key']}{i}", "")
        rows.append(row)
    return rows


def _rows_from_saved(question, answer):
    config = question.options
    data = (answer.data if answer else None) or {}
    rows = [
        {
            "name": item["name"],
            **{r["key"]: str(item.get(r["key"], "")) for r in config["ratings"]},
        }
        for item in data.get("items", [])
    ]
    empty = {"name": "", **{r["key"]: "" for r in config["ratings"]}}
    while len(rows) < config["max_items"]:
        rows.append(dict(empty))
    return rows


def parse_payload(question, post):
    """Formdan gelen veriyi API'deki cevap biçimine çevirir. Boşsa None döner."""
    prefix = _prefix(question)
    qtype = question.question_type

    if qtype in (Type.SCALE_012, Type.SINGLE_CHOICE):
        raw = post.get(f"{prefix}_value", "")
        if raw == "":
            return None
        payload = {"value": _to_int(raw)}
        if question.allows_explanation:
            payload["text"] = post.get(f"{prefix}_text", "").strip()[:MAX_TEXT]
        return payload

    if qtype == Type.FREE_TEXT:
        text = post.get(f"{prefix}_text", "").strip()[:MAX_TEXT]
        return {"text": text} if text else None

    if qtype == Type.ACTIVITY_LIST:
        none = post.get(f"{prefix}_none") == "on"
        filled = [row for row in _rows_from_post(question, post) if row["name"]]
        if not none and not filled:
            return None
        items = []
        for row in filled:
            item = {"name": row["name"]}
            for rating in question.options["ratings"]:
                item[rating["key"]] = _to_int(row[rating["key"]])
            items.append(item)
        return {"data": {"none": none, "items": items}}

    return None


def save_page(session, questions, post):
    """Sayfadaki cevapları doğrular ve kaydeder. {soru_id: hata mesajı} döndürür."""
    errors = {}
    existing = {
        a.question_id: a for a in session.answers.filter(question__in=questions)
    }

    for question in questions:
        if question.is_header:
            continue
        payload = parse_payload(question, post)
        if payload is None:
            # Serbest metin boşaltıldıysa eski cevabı sil.
            if question.question_type == Type.FREE_TEXT and question.id in existing:
                existing[question.id].delete()
            continue
        try:
            cleaned = answer_service.clean_answer(question, payload)
        except ValidationError:
            is_list = question.question_type == Type.ACTIVITY_LIST
            errors[question.id] = MSG_LIST if is_list else MSG_INVALID
            continue
        Answer.objects.update_or_create(
            session=session, question=question, defaults=cleaned
        )
    return errors


def missing_on_page(session, questions):
    required = set(
        answer_service.required_questions(session).values_list("id", flat=True)
    )
    answered = set(session.answers.values_list("question_id", flat=True))
    return {q.id for q in questions if q.id in required and q.id not in answered}


def _text_value(prefix, answer, post, use_post):
    if use_post:
        return post.get(f"{prefix}_text", "")
    return answer.text if answer else ""


def _row_cards(question, prefix, rows):
    cards = []
    for i, row in enumerate(rows):
        selects = []
        for rating in question.options["ratings"]:
            selects.append(
                {
                    "field": f"{prefix}_{rating['key']}{i}",
                    "label": rating["label"],
                    "options": [
                        {
                            "value": c["value"],
                            "label": c["label"],
                            "selected": str(c["value"]) == str(row[rating["key"]]),
                        }
                        for c in rating["choices"]
                    ],
                }
            )
        cards.append(
            {
                "index": i + 1,
                "name_field": f"{prefix}_name{i}",
                "name": row["name"],
                "selects": selects,
            }
        )
    return cards


def build_cards(questions, answers, errors, post):
    """Şablonun doğrudan çizeceği, her soru için hazır bir sözlük listesi üretir."""
    cards = []
    for question in questions:
        prefix = _prefix(question)
        answer = answers.get(question.id)
        use_post = post is not None and question.id in errors
        card = {
            "code": question.code,
            "show_code": question.code[0].isdigit(),
            "text": question.text,
            "depth": 1 if question.parent_id else 0,
            "header": question.is_header,
            "kind": KINDS.get(question.question_type),
            "field": prefix,
            "explain": question.allows_explanation,
            "error": errors.get(question.id, ""),
        }
        cards.append(card)
        if question.is_header:
            continue

        if card["kind"] in ("scale", "choice"):
            if use_post:
                selected = _to_int(post.get(f"{prefix}_value"))
            else:
                selected = answer.value if answer else None
            if card["kind"] == "scale":
                choices = [{"value": v, "label": str(v)} for v in (0, 1, 2)]
            else:
                choices = question.options
            card["choices"] = [
                {
                    "value": c["value"],
                    "label": c["label"],
                    "checked": c["value"] == selected,
                }
                for c in choices
            ]
            card["text_value"] = _text_value(prefix, answer, post, use_post)

        elif card["kind"] == "text":
            card["text_value"] = _text_value(prefix, answer, post, use_post)

        elif card["kind"] == "list":
            if use_post:
                card["none"] = post.get(f"{prefix}_none") == "on"
                rows = _rows_from_post(question, post)
            else:
                data = (answer.data if answer else None) or {}
                card["none"] = bool(data.get("none"))
                rows = _rows_from_saved(question, answer)
            card["rows"] = _row_cards(question, prefix, rows)
    return cards
