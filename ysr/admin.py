from django.contrib import admin
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from .models import PsychologistNote, Question, Respondent, Section, TestSession
from .services import answers as answer_service
from .services import report as report_service


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


class NoteInline(admin.StackedInline):
    model = PsychologistNote
    extra = 1
    fields = ("note",)


@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    list_display = (
        "respondent",
        "status",
        "progress_display",
        "started_at",
        "completed_at",
        "has_critical",
    )
    list_filter = ("status",)
    search_fields = ("respondent__code",)
    fields = (
        "respondent_info",
        "status",
        "started_at",
        "completed_at",
        "answer_report",
    )
    readonly_fields = fields
    inlines = [NoteInline]

    def has_add_permission(self, request):
        # Oturumlar yalnızca API üzerinden açılır.
        return False

    @admin.display(description="İlerleme")
    def progress_display(self, obj):
        p = answer_service.progress(obj)
        return f'{p["answered"]}/{p["total"]}'

    @admin.display(description="Kritik cevap", boolean=True)
    def has_critical(self, obj):
        return obj.answers.filter(question__is_critical=True, value__gt=0).exists()

    @admin.display(description="Katılımcı")
    def respondent_info(self, obj):
        r = obj.respondent
        parts = [r.code, r.get_gender_display(), f"{r.age} yaş"]
        if r.grade:
            parts.append(f"{r.grade}. sınıf")
        return " · ".join(parts)

    @admin.display(description="Sorular ve cevaplar")
    def answer_report(self, obj):
        html = render_to_string(
            "ysr/session_report.html", report_service.build_report(obj)
        )
        return mark_safe(html)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, PsychologistNote) and not obj.author_id:
                obj.author = request.user
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()
