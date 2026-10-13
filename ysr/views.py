from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Question, Section, TestSession
from .serializers import QuestionSerializer, RespondentSerializer, SectionSerializer


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
