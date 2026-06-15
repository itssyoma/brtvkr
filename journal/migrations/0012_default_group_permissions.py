from django.db import migrations


GROUP_PERMISSIONS = {
    "Учебная часть": {
        "journal": {
            "view_collegeinformation",
            "view_subject",
            "add_subject",
            "change_subject",
            "view_teachingassignment",
            "add_teachingassignment",
            "change_teachingassignment",
            "delete_teachingassignment",
            "view_curriculumplanitem",
            "view_lesson",
            "view_grade",
            "view_attendance",
            "view_journalchangelog",
            "view_student",
            "add_student",
            "change_student",
            "delete_student",
            "view_studygroup",
            "add_studygroup",
            "change_studygroup",
            "delete_studygroup",
            "view_academicyeararchive",
            "add_academicyeararchive",
            "change_academicyeararchive",
            "view_academicyeararchiveevent",
        },
    },
    "Преподаватели": {
        "journal": {
            "view_subject",
            "view_teachingassignment",
            "view_curriculumplanitem",
            "view_lesson",
            "view_grade",
            "view_attendance",
        },
    },
    "Кураторы": {
        "journal": {
            "view_subject",
            "view_teachingassignment",
            "view_lesson",
            "view_grade",
            "view_attendance",
            "view_student",
            "view_studygroup",
        },
    },
    "Аудиторы": {
        "journal": {
            "view_collegeinformation",
            "view_subject",
            "view_teachingassignment",
            "view_curriculumplanitem",
            "view_lesson",
            "view_grade",
            "view_attendance",
            "view_journalchangelog",
            "view_student",
            "view_studygroup",
            "view_academicyeararchive",
            "view_academicyeararchiveevent",
        },
    },
}


def assign_default_permissions(apps, schema_editor):
    group_model = apps.get_model("auth", "Group")
    permission_model = apps.get_model("auth", "Permission")

    administrators = group_model.objects.get(name="Администраторы")
    administrators.permissions.set(permission_model.objects.all())

    for group_name, app_permissions in GROUP_PERMISSIONS.items():
        group = group_model.objects.get(name=group_name)
        permissions = permission_model.objects.none()
        for app_label, codenames in app_permissions.items():
            permissions = permissions | permission_model.objects.filter(
                content_type__app_label=app_label,
                codename__in=codenames,
            )
        group.permissions.set(permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0011_default_user_groups"),
    ]

    operations = [
        migrations.RunPython(
            assign_default_permissions,
            migrations.RunPython.noop,
        ),
    ]
