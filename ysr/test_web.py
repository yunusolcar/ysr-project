from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Answer, Respondent, TestSession
from .services.pages import build_pages


class WebFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_questions", verbosity=0)

    def setUp(self):
        response = self.client.post(
            reverse("test-start"), {"code": "W1", "gender": "kiz", "age": 14}
        )
        self.session = TestSession.objects.get()
        self.assertRedirects(
            response,
            reverse("test-resume", args=[self.session.id]),
            fetch_redirect_response=False,
        )

    def page_url(self, index):
        return reverse("test-page", args=[self.session.id, index])

    def full_post(self, page):
        data = {}
        for q in page["questions"]:
            if q.is_header:
                continue
            field = f"q{q.id}"
            if q.question_type == "scale_012":
                data[f"{field}_value"] = "0"
            elif q.question_type == "single_choice":
                data[f"{field}_value"] = str(q.options[0]["value"])
            elif q.question_type == "activity_list":
                data[f"{field}_none"] = "on"
        return data

    def test_start_rejects_bad_age(self):
        response = self.client.post(
            reverse("test-start"), {"code": "W2", "gender": "kiz", "age": 9}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Respondent.objects.filter(code="W2").exists())

    def test_resume_goes_to_first_page(self):
        response = self.client.get(reverse("test-resume", args=[self.session.id]))
        self.assertRedirects(response, self.page_url(0))

    def test_page_renders_without_critical_wording(self):
        response = self.client.get(self.page_url(0))
        self.assertContains(response, "sporları yaz")
        self.assertNotContains(response, "kritik")

    def test_missing_answers_keep_user_on_page(self):
        response = self.client.post(self.page_url(0), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bu soruyu cevaplamayı unutma")
        self.assertEqual(Answer.objects.count(), 0)

    def test_valid_page_saves_and_moves_on(self):
        pages = build_pages()
        response = self.client.post(self.page_url(0), self.full_post(pages[0]))
        self.assertRedirects(response, self.page_url(1))
        self.assertEqual(Answer.objects.count(), 1)

    def test_activity_list_rows_are_saved(self):
        question = build_pages()[0]["questions"][0]
        field = f"q{question.id}"
        data = {
            f"{field}_name0": "Yüzme",
            f"{field}_time0": "1",
            f"{field}_skill0": "2",
        }
        self.client.post(self.page_url(0), data)
        answer = Answer.objects.get(question=question)
        self.assertEqual(
            answer.data,
            {"none": False, "items": [{"name": "Yüzme", "time": 1, "skill": 2}]},
        )

    def test_incomplete_activity_row_is_rejected(self):
        question = build_pages()[0]["questions"][0]
        response = self.client.post(
            self.page_url(0), {f"q{question.id}_name0": "Yüzme"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bütün seçenekleri")
        self.assertEqual(Answer.objects.count(), 0)

    def test_back_button_goes_to_previous_page(self):
        response = self.client.post(self.page_url(1), {"nav": "prev"})
        self.assertRedirects(response, self.page_url(0))

    def test_full_flow_completes_session(self):
        pages = build_pages()
        self.assertEqual(len(pages), 19)
        response = None
        for index, page in enumerate(pages):
            response = self.client.post(self.page_url(index), self.full_post(page))
            self.assertEqual(response.status_code, 302, index)
        self.assertRedirects(response, reverse("test-done", args=[self.session.id]))
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "completed")

        again = self.client.get(self.page_url(0))
        self.assertRedirects(again, reverse("test-done", args=[self.session.id]))
