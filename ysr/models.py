from django.db import models
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator


class Section(models.Model):
    """Testin bölümü. Örn: Bölüm 1 (Yetkinlikler), Bölüm 2 (Sorun maddeleri)."""

    code = models.SlugField("Kod", unique=True)
    title = models.CharField("Başlık", max_length=200)
    instructions = models.TextField("Yönerge", blank=True)
    order = models.PositiveIntegerField("Sıra", default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Bölüm"
        verbose_name_plural = "Bölümler"

    def __str__(self):
        return self.title


class Question(models.Model):
    """Testteki tek bir soru ya da madde."""

    class Type(models.TextChoices):
        ACTIVITY_LIST = "activity_list", "Liste + değerlendirme"
        SCALE_012 = "scale_012", "0-1-2 ölçeği"
        SINGLE_CHOICE = "single_choice", "Tek seçenek"
        FREE_TEXT = "free_text", "Serbest metin"

    section = models.ForeignKey(
        Section,
        verbose_name="Bölüm",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    code = models.CharField(
        "Kod",
        max_length=20,
        unique=True,
        help_text="Örn: 56a, 91, I.1. Formdaki numarayla aynı olsun.",
    )
    order = models.PositiveIntegerField(
        "Sıra",
        help_text="Çocuğa gösterilecek sıra. Tüm sorularda benzersiz olsun.",
    )
    parent = models.ForeignKey(
        "self",
        verbose_name="Üst madde",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        help_text="Alt maddeler için (56a-h → 56).",
    )
    text = models.TextField("Soru metni")
    question_type = models.CharField(
        "Soru tipi",
        max_length=20,
        choices=Type.choices,
        default=Type.SCALE_012,
    )
    options = models.JSONField(
        "Seçenekler",
        default=list,
        blank=True,
        help_text='Tek seçenek tipinde bir liste, "Liste + değerlendirme" tipinde bir sözlük.',
    )
    allows_explanation = models.BooleanField(
        "Açıklama alanı var",
        default=False,
        help_text='Formda "açıklayınız" yazan maddeler.',
    )
    is_critical = models.BooleanField(
        "Kritik madde",
        default=False,
        help_text="Kendine zarar / intihar gibi psikoloğun mutlaka görmesi gereken maddeler.",
    )

    is_header = models.BooleanField(
        "Başlık maddesi",
        default=False,
        help_text="Cevap alınmaz, sadece alt maddeleri gruplar (örn. 56).",
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Soru"
        verbose_name_plural = "Sorular"

    def __str__(self):
        return f"{self.code}. {self.text[:60]}"


class Respondent(models.Model):
    """Testi çözen genç. Formun üst kısmındaki bilgiler."""

    class Gender(models.TextChoices):
        MALE = "erkek", "Erkek"
        FEMALE = "kiz", "Kız"

    code = models.CharField(
        "Kod / takma ad",
        max_length=50,
        unique=True,
        help_text="Gerçek ad yerine kod kullan. Örn: T001.",
    )
    gender = models.CharField("Cinsiyet", max_length=10, choices=Gender.choices)
    age = models.PositiveSmallIntegerField(
        "Yaş",
        validators=[MinValueValidator(11), MaxValueValidator(18)],
    )
    birth_date = models.DateField("Doğum tarihi", null=True, blank=True)
    grade = models.CharField("Sınıf", max_length=30, blank=True)
    job = models.CharField("Çalışıyorsa işi", max_length=100, blank=True)
    parent1_work = models.CharField(
        "Baba / 1. ebeveynin işi", max_length=100, blank=True
    )
    parent2_work = models.CharField(
        "Anne / 2. ebeveynin işi", max_length=100, blank=True
    )
    ethnic_group = models.CharField("Etnik köken", max_length=100, blank=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "Katılımcı"
        verbose_name_plural = "Katılımcılar"

    def __str__(self):
        return f"{self.code} ({self.age})"


class TestSession(models.Model):
    """Bir katılımcının testi çözme oturumu."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Devam ediyor"
        COMPLETED = "completed", "Tamamlandı"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    respondent = models.ForeignKey(
        Respondent,
        verbose_name="Katılımcı",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    status = models.CharField(
        "Durum",
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    started_at = models.DateTimeField("Başlangıç", auto_now_add=True)
    completed_at = models.DateTimeField("Bitiş", null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Test oturumu"
        verbose_name_plural = "Test oturumları"

    def __str__(self):
        return f"{self.respondent.code} - {self.started_at:%d.%m.%Y %H:%M}"


class Answer(models.Model):
    """Bir oturumdaki tek bir sorunun cevabı."""

    session = models.ForeignKey(
        TestSession,
        verbose_name="Oturum",
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        verbose_name="Soru",
        on_delete=models.PROTECT,
        related_name="answers",
    )
    value = models.SmallIntegerField(
        "Değer",
        null=True,
        blank=True,
        help_text="0-1-2 ölçeği ve tek seçenek cevapları.",
    )
    text = models.TextField(
        "Metin",
        blank=True,
        help_text="Serbest metin cevapları ve 'açıklayınız' alanları.",
    )
    data = models.JSONField(
        "Yapılandırılmış veri",
        null=True,
        blank=True,
        help_text="Liste + değerlendirme tipi (spor, hobi vb.) cevapları.",
    )
    answered_at = models.DateTimeField("Cevaplama zamanı", auto_now=True)

    class Meta:
        ordering = ["question__order"]
        verbose_name = "Cevap"
        verbose_name_plural = "Cevaplar"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "question"],
                name="unique_answer_per_question",
            )
        ]

    def __str__(self):
        return f"{self.session_id} / {self.question.code}"


class PsychologistNote(models.Model):
    """Psikoloğun bir oturum hakkındaki yorumu."""

    session = models.ForeignKey(
        TestSession,
        verbose_name="Oturum",
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Yazan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    note = models.TextField("Not")
    created_at = models.DateTimeField("Tarih", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Psikolog notu"
        verbose_name_plural = "Psikolog notları"

    def __str__(self):
        return f"Not: {self.session_id}"
