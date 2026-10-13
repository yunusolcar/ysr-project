from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Answer, Question, Section, TestSession
from .serializers import (
    AnswerSerializer,
    AnswerInputSerializer,
    QuestionSerializer,
    RespondentSerializer,
    SectionSerializer,
)
from .services import answers as answer_service


@api_view(["POST"])
def start_session(request):
    """Katılımcıyı kaydeder ve yeni bir test oturumu açar."""
    serializer = RespondentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    with transaction.atomic():
        respondent = serializer.save()
        session = TestSession.objects.create(respondent=respondent)

    return Response(
        {"session_id": session.id, "status": session.status},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def session_questions(request, session_id):
    """Oturumun bölümlerini ve tüm soruları sıralı verir."""
    session = get_object_or_404(TestSession, pk=session_id)
    questions = Question.objects.select_related("section", "parent")

    return Response(
        {
            "session_id": session.id,
            "status": session.status,
            "sections": SectionSerializer(Section.objects.all(), many=True).data,
            "questions": QuestionSerializer(questions, many=True).data,
        }
    )


@api_view(["GET"])
def session_answers(request, session_id):
    """Şimdiye kadar verilen cevaplar ve ilerleme. Yarıda kalan testi devam ettirmek için."""
    session = get_object_or_404(TestSession, pk=session_id)
    answers = session.answers.select_related("question")

    return Response(
        {
            "session_id": session.id,
            "status": session.status,
            "progress": answer_service.progress(session),
            "answers": AnswerSerializer(answers, many=True).data,
        }
    )


@api_view(["PUT"])
def put_answer(request, session_id, question_code):
    """Bir soruya cevap kaydeder. Cevap varsa günceller (idempotent)."""
    session = get_object_or_404(TestSession, pk=session_id)
    if session.status == TestSession.Status.COMPLETED:
        return Response(
            {"detail": "This session is already completed."},
            status=status.HTTP_409_CONFLICT,
        )

    question = get_object_or_404(Question, code=question_code)

    payload = AnswerInputSerializer(data=request.data)
    payload.is_valid(raise_exception=True)
    cleaned = answer_service.clean_answer(question, payload.validated_data)

    answer, created = Answer.objects.update_or_create(
        session=session, question=question, defaults=cleaned
    )
    return Response(
        AnswerSerializer(answer).data,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["POST"])
def complete_session(request, session_id):
    """Eksik zorunlu soru yoksa oturumu tamamlandı olarak işaretler."""
    session = get_object_or_404(TestSession, pk=session_id)

    if session.status == TestSession.Status.COMPLETED:
        return Response(
            {
                "session_id": session.id,
                "status": session.status,
                "completed_at": session.completed_at,
            }
        )

    missing = answer_service.missing_codes(session)
    if missing:
        return Response(
            {"detail": "Some required questions are not answered.", "missing": missing},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session.status = TestSession.Status.COMPLETED
    session.completed_at = timezone.now()
    session.save(update_fields=["status", "completed_at"])

    return Response(
        {
            "session_id": session.id,
            "status": session.status,
            "completed_at": session.completed_at,
        }
    )
