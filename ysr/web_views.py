from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import StartForm
from .models import TestSession
from .services import answers as answer_service
from .services import webform
from .services.pages import build_pages


def start(request):
    form = StartForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            respondent = form.save()
            session = TestSession.objects.create(respondent=respondent)
        return redirect("test-resume", session_id=session.id)
    return render(request, "ysr/web/start.html", {"form": form})


def resume(request, session_id):
    """Oturumu, cevaplanmamış zorunlu soru içeren ilk sayfadan devam ettirir."""
    session = get_object_or_404(TestSession, pk=session_id)
    if session.status == TestSession.Status.COMPLETED:
        return redirect("test-done", session_id=session.id)

    pages = build_pages()
    required = set(
        answer_service.required_questions(session).values_list("id", flat=True)
    )
    answered = set(session.answers.values_list("question_id", flat=True))
    pending = required - answered

    for index, page in enumerate(pages):
        if any(q.id in pending for q in page["questions"]):
            return redirect("test-page", session_id=session.id, page=index)
    return redirect("test-page", session_id=session.id, page=len(pages) - 1)


def question_page(request, session_id, page):
    session = get_object_or_404(TestSession, pk=session_id)
    if session.status == TestSession.Status.COMPLETED:
        return redirect("test-done", session_id=session.id)

    pages = build_pages()
    if not 0 <= page < len(pages):
        raise Http404("Sayfa bulunamadı")
    current = pages[page]
    questions = current["questions"]
    is_last = page == len(pages) - 1

    errors = {}
    post = None
    if request.method == "POST":
        post = request.POST
        errors = webform.save_page(session, questions, post)
        if post.get("nav") == "prev" and page > 0:
            return redirect("test-page", session_id=session.id, page=page - 1)

    if request.method == "POST" or request.GET.get("eksik"):
        for question_id in webform.missing_on_page(session, questions):
            errors.setdefault(question_id, webform.MSG_MISSING)

    if request.method == "POST" and not errors:
        if not is_last:
            return redirect("test-page", session_id=session.id, page=page + 1)
        return _finish(session, pages)

    answers = {a.question_id: a for a in session.answers.all()}
    progress = answer_service.progress(session)
    cards = webform.build_cards(questions, answers, errors, post)
    percent = (
        round(100 * progress["answered"] / progress["total"])
        if progress["total"]
        else 0
    )

    return render(
        request,
        "ysr/web/page.html",
        {
            "cards": cards,
            "title": current["title"],
            "instructions": current["instructions"],
            "page_number": page + 1,
            "total_pages": len(pages),
            "has_back": page > 0,
            "is_last": is_last,
            "progress": progress,
            "percent": percent,
            "error_count": len(errors),
            "has_scale": any(c["kind"] == "scale" and not c["header"] for c in cards),
        },
    )


def _finish(session, pages):
    missing = set(answer_service.mark_completed(session))
    if not missing:
        return redirect("test-done", session_id=session.id)
    # Eksik soru önceki bir sayfadaysa oraya götür.
    for index, page in enumerate(pages):
        if any(q.code in missing for q in page["questions"]):
            url = reverse("test-page", args=[session.id, index])
            return redirect(f"{url}?eksik=1")
    return redirect("test-resume", session_id=session.id)


def done(request, session_id):
    session = get_object_or_404(TestSession, pk=session_id)
    if session.status != TestSession.Status.COMPLETED:
        return redirect("test-resume", session_id=session.id)
    return render(request, "ysr/web/done.html")
