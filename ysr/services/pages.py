from ysr.models import Question

PAGE_SIZE = 10


def build_pages():
    """Soruları çocuğa gösterilecek sayfalara böler.

    Bölüm 1: aynı Romen rakamıyla başlayan sorular bir sayfada (I, II, ... VII).
    Bölüm 2: 10 madde bir sayfada. Alt maddeler üst maddesiyle aynı sayfada kalır.
    """
    pages = []
    page_of = {}
    for question in Question.objects.select_related("section"):
        if question.parent_id:
            page = page_of[question.parent_id]
        else:
            page = _page_for(question, pages)
            page["top_count"] += 1
        page["questions"].append(question)
        page_of[question.id] = page
    return pages


def _page_for(question, pages):
    section = question.section
    key = question.code.split(".")[0] if section.code == "bolum-1" else None
    last = pages[-1] if pages else None

    if last and last["section"] == section.code:
        if key is not None and last["key"] == key:
            return last
        if key is None and last["top_count"] < PAGE_SIZE:
            return last

    page = {
        "section": section.code,
        "title": section.title,
        "instructions": section.instructions,
        "key": key,
        "top_count": 0,
        "questions": [],
    }
    pages.append(page)
    return page
