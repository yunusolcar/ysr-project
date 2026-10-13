from django.urls import path

from . import views

urlpatterns = [
    path("sessions/", views.start_session),
    path("sessions/<uuid:session_id>/questions/", views.session_questions),
]
