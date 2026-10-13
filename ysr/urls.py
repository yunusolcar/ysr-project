from django.urls import path

from . import views

urlpatterns = [
    path("sessions/", views.start_session),
    path("sessions/<uuid:session_id>/questions/", views.session_questions),
    path("sessions/<uuid:session_id>/answers/", views.session_answers),
    path("sessions/<uuid:session_id>/answers/<str:question_code>/", views.put_answer),
    path("sessions/<uuid:session_id>/complete/", views.complete_session),
]
