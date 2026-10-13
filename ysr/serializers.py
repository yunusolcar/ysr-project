from rest_framework import serializers

from .models import Question, Respondent, Section


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
