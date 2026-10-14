import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from ysr.models import Answer, Question, Respondent, TestSession
from ysr.services import answers as answer_service

Type = Question.Type

ACTIVITIES = {
    "I": [
        {"name": "Yüzme", "time": 2, "skill": 1},
        {"name": "Futbol", "time": 1, "skill": 1},
    ],
    "II": [
        {"name": "Video oyunları", "time": 2, "skill": 2},
        {"name": "Kitap okumak", "time": 1, "skill": 1},
    ],
    "III": [{"name": "Okul satranç kulübü", "active": 1}],
    "IV": [{"name": "Bulaşık yıkamak", "skill": 1}],
    "VII.1e": [{"name": "İngilizce", "grade": 2}],
}
FIXED_CHOICES = {
    "V.1": 2,
    "V.2": 1,
    "VII.0": 1,
    "VII.2": 0,
    **{f"VII.1{c}": 2 for c in "abcd"},
}
FREE_TEXTS = {
    "VII.3": "Matematik dersinde bazen zorlanıyorum.",
    "VII.4": "Bazen kendimi yalnız hissediyorum.",
    "VII.5": "Hayvanlara karşı sevecenim, iyi bir arkadaşım.",
}


class Command(BaseCommand):
    help = "Sunum için örnek katılımcı ve oturumlar oluşturur. Tekrar çalıştırılabilir."

    @transaction.atomic
    def handle(self, *args, **options):
        questions = list(Question.objects.filter(is_header=False))
        if not questions:
            raise CommandError("Soru bankası boş. Önce: py .\\manage.py load_questions")

        Respondent.objects.filter(code__in=["DEMO01", "DEMO02"]).delete()

        done = self.build(
            questions, "DEMO01", "kiz", 14, "8", {"91": 1, "18": 0}, None, True
        )
        part = self.build(
            questions, "DEMO02", "erkek", 16, "10", {"91": 0, "18": 0}, 45, False
        )

        self.stdout.write(self.style.SUCCESS("Örnek veri hazır."))
        self.stdout.write(f"DEMO01 (tamamlandı, kritik madde işaretli): {done.id}")
        self.stdout.write(f"DEMO02 (yarım kaldı): {part.id}")

    def build(self, questions, code, gender, age, grade, overrides, limit, complete):
        respondent = Respondent.objects.create(
            code=code, gender=gender, age=age, grade=grade
        )
        session = TestSession.objects.create(respondent=respondent)
        rng = random.Random(code)

        for question in (questions[:limit] if limit else questions):
            payload = self.payload_for(question, rng, overrides)
            if payload is None:
                continue
            cleaned = answer_service.clean_answer(question, payload)
            Answer.objects.create(session=session, question=question, **cleaned)

        if complete:
            if answer_service.missing_codes(session):
                raise CommandError(
                    f"{code}: eksik zorunlu soru kaldı, oturum tamamlanamadı."
                )
            session.status = TestSession.Status.COMPLETED
            session.completed_at = timezone.now()
            session.save(update_fields=["status", "completed_at"])
        return session

    def payload_for(self, question, rng, overrides):
        qtype = question.question_type
        if qtype == Type.SCALE_012:
            value = overrides.get(question.code)
            if value is None:
                value = rng.choices([0, 1, 2], weights=[65, 25, 10])[0]
            payload = {"value": value}
            if question.allows_explanation and value > 0:
                payload["text"] = "Örnek açıklama (demo verisi)"
            return payload
        if qtype == Type.SINGLE_CHOICE:
            options = question.options
            default = options[1]["value"] if len(options) > 1 else options[0]["value"]
            return {"value": FIXED_CHOICES.get(question.code, default)}
        if qtype == Type.FREE_TEXT:
            text = FREE_TEXTS.get(question.code)
            return {"text": text} if text else None
        if qtype == Type.ACTIVITY_LIST:
            return {"data": {"none": False, "items": ACTIVITIES[question.code]}}
        return None
