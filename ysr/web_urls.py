from django.urls import path

from . import web_views as views

urlpatterns = [
    path("", views.start, name="test-start"),
    path("test/<uuid:session_id>/", views.resume, name="test-resume"),
    path(
        "test/<uuid:session_id>/sayfa/<int:page>/",
        views.question_page,
        name="test-page",
    ),
    path("test/<uuid:session_id>/bitti/", views.done, name="test-done"),
]
