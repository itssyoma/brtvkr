from django.urls import path

from . import views


app_name = "journal"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "assignments/<int:assignment_id>/",
        views.assignment_detail,
        name="assignment_detail",
    ),
    path(
        "assignments/<int:assignment_id>/autosave/",
        views.autosave_journal_cell,
        name="autosave_journal_cell",
    ),
    path(
        "assignments/<int:assignment_id>/curriculum/import/",
        views.import_curriculum,
        name="import_curriculum",
    ),
    path(
        "assignments/<int:assignment_id>/curriculum/",
        views.curriculum_plan,
        name="curriculum_plan",
    ),
    path(
        "assignments/<int:assignment_id>/curriculum/<int:item_id>/delete/",
        views.delete_curriculum_item,
        name="delete_curriculum_item",
    ),
    path("lessons/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path(
        "lessons/<int:lesson_id>/delete/",
        views.delete_lesson,
        name="delete_lesson",
    ),
]
