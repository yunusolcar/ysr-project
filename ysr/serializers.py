from rest_framework import serializers

from .models import Answer, Question, Respondent, Section


class RespondentSerializer(serializers.ModelSerializer):
    """Oturum başlatırken gelen katılımcı bilgisini doğrular ve kaydeder."""

    class Meta:
        model = Respondent
        fields = [
            "code",
            "gender",
            "age",
            "birth_date",
            "grade",
            "job",
            "parent1_work",
            "parent2_work",
            "ethnic_group",
        ]


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["code", "title", "instructions", "order"]


class QuestionSerializer(serializers.ModelSerializer):
    section = serializers.SlugRelatedField(slug_field="code", read_only=True)
    parent = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = Question
        fields = [
            "code",
            "order",
            "section",
            "parent",
            "text",
            "question_type",
            "options",
            "allows_explanation",
            "is_header",
        ]


class AnswerInputSerializer(serializers.Serializer):
    """Gelen cevabın şekil kontrolü. Tip kontrolü services/answers.py'de."""

    value = serializers.IntegerField(required=False, allow_null=True)
    text = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    data = serializers.JSONField(required=False, allow_null=True)


class AnswerSerializer(serializers.ModelSerializer):
    question = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = Answer
        fields = ["question", "value", "text", "data", "answered_at"]
