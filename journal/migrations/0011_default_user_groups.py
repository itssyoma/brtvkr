from django.db import migrations


DEFAULT_GROUP_NAMES = (
    "Администраторы",
    "Учебная часть",
    "Преподаватели",
    "Кураторы",
    "Аудиторы",
)


def create_default_groups(apps, schema_editor):
    group_model = apps.get_model("auth", "Group")
    for name in DEFAULT_GROUP_NAMES:
        group_model.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("journal", "0010_user_profile"),
    ]

    operations = [
        migrations.RunPython(
            create_default_groups,
            migrations.RunPython.noop,
        ),
    ]
