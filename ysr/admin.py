from django.contrib import admin

from .models import Answer, PsychologistNote, Question, Respondent, Section, TestSession


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "code")
    ordering = ("order",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "code",
        "short_text",
        "question_type",
        "section",
        "is_critical",
        "is_header",
    )
    list_filter = ("section", "question_type", "is_critical", "is_header")
    search_fields = ("code", "text")
    ordering = ("order",)

    @admin.display(description="Soru metni")
    def short_text(self, obj):
        return obj.text[:70]


@admin.register(Respondent)
class RespondentAdmin(admin.ModelAdmin):
    list_display = ("code", "gender", "age", "grade", "created_at")
    search_fields = ("code",)


class AnswerInline(admin.TabularInline):
    """Oturum sayfasında cevapları soru sırasıyla, salt okunur gösterir."""

    model = Answer
    extra = 0
    can_delete = False
    fields = ("question_code", "question_text", "is_critical", "value", "text", "data")
    readonly_fields = fields
    ordering = ("question__order",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("question")

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Kod")
    def question_code(self, obj):
        return obj.question.code

    @admin.display(description="Soru")
    def question_text(self, obj):
        return obj.question.text[:80]

    @admin.display(description="Kritik", boolean=True)
    def is_critical(self, obj):
        return obj.question.is_critical


class NoteInline(admin.StackedInline):
    model = PsychologistNote
    extra = 1
    fields = ("note",)


@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    list_display = (
        "respondent",
        "status",
        "started_at",
        "completed_at",
        "has_critical",
    )
    list_filter = ("status",)
    search_fields = ("respondent__code",)
    readonly_fields = ("id", "respondent", "started_at", "completed_at")
    inlines = [NoteInline, AnswerInline]

    @admin.display(description="Kritik cevap", boolean=True)
    def has_critical(self, obj):
        return obj.answers.filter(question__is_critical=True, value__gt=0).exists()

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, PsychologistNote) and not obj.author_id:
                obj.author = request.user
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()
