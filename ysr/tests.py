from django.core.management import call_command
from rest_framework.test import APITestCase

from .models import Answer, Question


class SessionApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_questions", verbosity=0)

    def setUp(self):
        response = self.client.post(
            "/api/sessions/",
            {"code": "T001", "gender": "kiz", "age": 14},
            format="json",
        )
        self.session_id = response.data["session_id"]
        self.base = f"/api/sessions/{self.session_id}"

    # -- yardımcılar --------------------------------------------------
    def put(self, code, payload):
        return self.client.put(f"{self.base}/answers/{code}/", payload, format="json")

    def answer_all(self, skip_prefix=None):
        questions = Question.objects.filter(is_header=False).exclude(
            question_type="free_text"
        )
        for q in questions:
            if skip_prefix and q.code.startswith(skip_prefix):
                continue
            if q.question_type == "scale_012":
                payload = {"value": 0}
            elif q.question_type == "single_choice":
                payload = {"value": q.options[0]["value"]}
            else:
                payload = {"data": {"none": True}}
            self.assertEqual(self.put(q.code, payload).status_code, 201, q.code)

    # -- oturum ve sorular ---------------------------------------------
    def test_start_session_rejects_bad_age(self):
        response = self.client.post(
            "/api/sessions/",
            {"code": "T002", "gender": "kiz", "age": 10},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_questions_endpoint_hides_critical_flag(self):
        response = self.client.get(f"{self.base}/questions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["questions"]), 143)
        self.assertNotIn("is_critical", response.data["questions"][0])

    # -- cevap kaydetme ------------------------------------------------
    def test_scale_answer_is_saved_and_updated(self):
        self.assertEqual(self.put("3", {"value": 1}).status_code, 201)
        self.assertEqual(self.put("3", {"value": 2}).status_code, 200)
        self.assertEqual(Answer.objects.count(), 1)
        self.assertEqual(Answer.objects.get().value, 2)

    def test_scale_rejects_out_of_range(self):
        self.assertEqual(self.put("3", {"value": 3}).status_code, 400)
        self.assertEqual(self.put("3", {}).status_code, 400)
        self.assertEqual(self.put("3", {"value": "abc"}).status_code, 400)

    def test_header_cannot_be_answered(self):
        self.assertEqual(self.put("56", {"value": 1}).status_code, 400)
        self.assertEqual(self.put("999", {"value": 1}).status_code, 404)

    def test_single_choice_validates_options(self):
        self.assertEqual(self.put("V.1", {"value": 5}).status_code, 400)
        self.assertEqual(self.put("V.1", {"value": 2}).status_code, 201)

    def test_text_only_when_explanation_allowed(self):
        self.assertEqual(self.put("3", {"value": 1, "text": "x"}).status_code, 400)
        self.assertEqual(self.put("2", {"value": 1, "text": "once"}).status_code, 201)

    def test_activity_list_valid(self):
        payload = {
            "data": {"none": False, "items": [{"name": "Yüzme", "time": 1, "skill": 2}]}
        }
        self.assertEqual(self.put("I", payload).status_code, 201)
        self.assertEqual(self.put("I", {"data": {"none": True}}).status_code, 200)

    def test_activity_list_invalid(self):
        bad_rating = {"data": {"items": [{"name": "Yüzme", "time": 5, "skill": 1}]}}
        too_many = {
            "data": {
                "items": [{"name": str(i), "time": 1, "skill": 1} for i in range(4)]
            }
        }
        conflict = {
            "data": {"none": True, "items": [{"name": "x", "time": 1, "skill": 1}]}
        }
        for payload in (bad_rating, too_many, conflict, {"value": 1}, {}):
            self.assertEqual(self.put("I", payload).status_code, 400)

    # -- devam etme ve bitirme -----------------------------------------
    def test_progress_endpoint_supports_resume(self):
        before = self.client.get(f"{self.base}/answers/").data
        self.put("3", {"value": 0})
        after = self.client.get(f"{self.base}/answers/").data
        self.assertEqual(before["progress"]["answered"], 0)
        self.assertEqual(after["progress"]["answered"], 1)
        self.assertEqual(after["answers"][0]["question"], "3")

    def test_complete_fails_when_items_missing(self):
        self.put("3", {"value": 0})
        response = self.client.post(f"{self.base}/complete/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("I", response.data["missing"])
        self.assertNotIn("3", response.data["missing"])

    def test_complete_succeeds_and_locks_session(self):
        self.answer_all()
        response = self.client.post(f"{self.base}/complete/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "completed")
        self.assertNotIn("has_critical", response.data)
        self.assertEqual(self.put("3", {"value": 1}).status_code, 409)

    def test_not_attending_school_skips_school_subjects(self):
        self.answer_all(skip_prefix="VII.1")
        self.put("VII.0", {"value": 0})
        response = self.client.post(f"{self.base}/complete/")
        self.assertEqual(response.status_code, 200)
