from django import template

from journal.models import (
    AcademicYearArchive,
    AcademicYearArchiveEvent,
    CollegeInformation,
    Lesson,
    Student,
    StudyGroup,
    TeachingAssignment,
    user_full_name,
)
from journal.version import APP_VERSION


register = template.Library()


@register.filter
def full_user_name(user):
    return user_full_name(user)


@register.inclusion_tag(
    "admin/journal/dashboard_summary.html",
    takes_context=True,
)
def journal_admin_dashboard(context):
    request = context["request"]
    college = CollegeInformation.get_current()
    last_archive_event = (
        AcademicYearArchiveEvent.objects.select_related(
            "archive",
            "user",
        ).first()
    )
    return {
        "college": college,
        "display_name": user_full_name(request.user),
        "student_count": Student.objects.filter(is_active=True).count(),
        "group_count": StudyGroup.objects.count(),
        "assignment_count": TeachingAssignment.objects.count(),
        "lesson_count": Lesson.objects.count(),
        "open_years": list(
            AcademicYearArchive.objects.filter(
                is_locked=False
            ).order_by("-academic_year")
        ),
        "archived_year_count": AcademicYearArchive.objects.filter(
            is_locked=True
        ).count(),
        "last_archive_event": last_archive_event,
        "app_version": APP_VERSION,
    }
