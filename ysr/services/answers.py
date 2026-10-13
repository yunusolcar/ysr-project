from rest_framework.exceptions import ValidationError

from ysr.models import Answer, Question

Type = Question.Type

SCALE_012_CHOICES = [{"value": 0}, {"value": 1}, {"value": 2}]
MAX_ITEM_NAME = 100


def _is_int(value):
    # bool, Python'da int'in alt sınıfı; true/false'u sayı olarak kabul etmiyoruz.
    return isinstance(value, int) and not isinstance(value, bool)


def _allowed(choices):
    return [choice["value"] for choice in choices]


def _check_choice(value, choices, field):
    if not _is_int(value) or value not in _allowed(choices):
        raise ValidationError({field: f"Must be one of {_allowed(choices)}."})


def _clean_activity_list(question, data):
    config = question.options
    if not isinstance(data, dict):
        raise ValidationError(
            {"data": 'Expected an object like {"none": false, "items": [...]}.'}
        )

    none = data.get("none", False)
    items = data.get("items", [])
    if not isinstance(none, bool) or not isinstance(items, list):
        raise ValidationError({"data": "'none' must be a boolean and 'items' a list."})

    if none:
        if items:
            raise ValidationError({"data": "'none' cannot be combined with items."})
        return {"none": True, "items": []}

    if not 1 <= len(items) <= config["max_items"]:
        raise ValidationError(
            {
                "data": f"Provide 1 to {config['max_items']} items, or set 'none' to true."
            }
        )

    cleaned = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValidationError({"data": f"Item {index} must be an object."})
        name = item.get("name")
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name.strip()) > MAX_ITEM_NAME
        ):
            raise ValidationError(
                {
                    "data": f"Item {index}: 'name' is required (max {MAX_ITEM_NAME} characters)."
                }
            )
        row = {"name": name.strip()}
        for rating in config["ratings"]:
            key = rating["key"]
            value = item.get(key)
            if not _is_int(value) or value not in _allowed(rating["choices"]):
                raise ValidationError(
                    {
                        "data": f"Item {index}: '{key}' must be one of {_allowed(rating['choices'])}."
                    }
                )
            row[key] = value
        cleaned.append(row)
    return {"none": False, "items": cleaned}


def clean_answer(question, payload):
    """Cevabı soru tipine göre doğrular. Kaydedilecek {value, text, data} sözlüğünü döndürür."""
    if question.is_header:
        raise ValidationError("This item is a heading and cannot be answered.")

    value = payload.get("value")
    text = payload.get("text", "")
    data = payload.get("data")
    qtype = question.question_type

    if text and not (question.allows_explanation or qtype == Type.FREE_TEXT):
        raise ValidationError({"text": "This question does not accept an explanation."})
    if qtype != Type.ACTIVITY_LIST and data is not None:
        raise ValidationError({"data": "This question does not accept 'data'."})

    if qtype == Type.SCALE_012:
        _check_choice(value, SCALE_012_CHOICES, "value")
        return {"value": value, "text": text, "data": None}

    if qtype == Type.SINGLE_CHOICE:
        _check_choice(value, question.options, "value")
        return {"value": value, "text": text, "data": None}

    if qtype == Type.FREE_TEXT:
        if value is not None:
            raise ValidationError({"value": "This question does not accept 'value'."})
        if not text:
            raise ValidationError({"text": "Text is required."})
        return {"value": None, "text": text, "data": None}

    if qtype == Type.ACTIVITY_LIST:
        if value is not None:
            raise ValidationError({"value": "This question does not accept 'value'."})
        return {"value": None, "text": "", "data": _clean_activity_list(question, data)}

    raise ValidationError("Unsupported question type.")


def required_questions(session):
    """Testi bitirmek için cevaplanması gereken sorular.

    - Başlık maddeleri cevap almaz.
    - Serbest metin soruları zorunlu değil.
    - Katılımcı okula gitmiyorsa (VII.0 = 0) okul dersleri (VII.1*) zorunlu değil.
    """
    questions = Question.objects.filter(is_header=False).exclude(
        question_type=Type.FREE_TEXT
    )
    attends_school = (
        Answer.objects.filter(session=session, question__code="VII.0")
        .values_list("value", flat=True)
        .first()
    )
    if attends_school == 0:
        questions = questions.exclude(code__startswith="VII.1")
    return questions


def missing_codes(session):
    return list(
        required_questions(session)
        .exclude(answers__session=session)
        .values_list("code", flat=True)
    )


def progress(session):
    required = required_questions(session)
    return {
        "answered": required.filter(answers__session=session).count(),
        "total": required.count(),
    }
