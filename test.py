import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from ysr.models import Respondent, TestSession, Question, Answer

# Katılımcı
r, created = Respondent.objects.get_or_create(
    code="T001", defaults={"gender": "erkek", "age": 13}
)

# Test oturumu (Her çalıştırmada yeni bir oturum açar)
s = TestSession.objects.create(respondent=r)

# Soruları veritabanından bul, yoksa hata vermemesi için oluşturalım (Test amaçlı)
q91, _ = Question.objects.get_or_create(code="91", defaults={"text": "Örnek soru 91"})
q3, _ = Question.objects.get_or_create(code="3", defaults={"text": "Örnek soru 3"})
qi, _ = Question.objects.get_or_create(code="I", defaults={"text": "Spor listesi"})

# Cevap eklemeleri
Answer.objects.create(session=s, question=q91, value=1)
Answer.objects.create(session=s, question=q3, value=0)
Answer.objects.create(
    session=s,
    question=qi,
    data={"none": False, "items": [{"name": "Yüzme", "time": 1, "skill": 2}]},
)

print(f"Başarılı! Toplam cevap sayısı: {s.answers.count()} (3 çıkmalı)")
