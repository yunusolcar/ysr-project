from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Answer, Question, Respondent, TestSession
from .services.report import build_report


class ReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_questions", verbosity=0)
        respondent = Respondent.objects.create(code="R1", gender="erkek", age=15)
        cls.session = TestSession.objects.create(respondent=respondent)

        def answer(code, **fields):
            Answer.objects.create(
                session=cls.session, question=Question.objects.get(code=code), **fields
            )

        answer("91", value=2)
        answer("3", value=0)
        answer("V.1", value=2)
        answer("2", value=1, text="bir kez denedim")
        answer(
            "I",
            data={"none": False, "items": [{"name": "Yüzme", "time": 1, "skill": 2}]},
        )

    def row(self, code):
        return next(r for r in build_report(self.session)["rows"] if r["code"] == code)

    def test_all_questions_in_order(self):
        rows = build_report(self.session)["rows"]
        self.assertEqual(len(rows), 143)
        self.assertEqual(rows[0]["code"], "I")

    def test_answers_are_human_readable(self):
        self.assertEqual(self.row("91")["lines"], ["2 – Çok ya da sık sık doğru"])
        self.assertEqual(self.row("V.1")["lines"], ["2 ya da 3"])
        self.assertEqual(
            self.row("I")["lines"],
            ["Yüzme — Zaman: Ortalama; Başarı: Ortalamanın üstünde"],
        )
        self.assertEqual(self.row("2")["explanation"], "bir kez denedim")

    def test_unanswered_and_critical(self):
        self.assertFalse(self.row("4")["answered"])
        critical = build_report(self.session)["critical"]
        self.assertEqual([r["code"] for r in critical], ["91"])

    def test_zero_on_critical_item_is_not_flagged(self):
        Answer.objects.create(
            session=self.session, question=Question.objects.get(code="18"), value=0
        )
        critical = build_report(self.session)["critical"]
        self.assertEqual([r["code"] for r in critical], ["91"])

    def test_admin_page_renders(self):
        admin_user = get_user_model().objects.create_superuser(
            "admin1", "a@example.com", "pw12345!"
        )
        self.client.force_login(admin_user)
        response = self.client.get(
            reverse("admin:ysr_testsession_change", args=[self.session.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yüzme")
        self.assertContains(response, "Kritik")
