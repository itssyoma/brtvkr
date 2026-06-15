import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("journal", "0004_curriculum_plan_and_grading"),
    ]

    operations = [
        migrations.CreateModel(
            name="JournalChangeLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="дата и время",
                    ),
                ),
                (
                    "lesson_date",
                    models.DateField(verbose_name="дата занятия"),
                ),
                (
                    "lesson_topic",
                    models.CharField(
                        max_length=500,
                        verbose_name="тема занятия",
                    ),
                ),
                (
                    "student_name",
                    models.CharField(
                        blank=True,
                        max_length=320,
                        verbose_name="ФИО студента",
                    ),
                ),
                (
                    "entity_type",
                    models.CharField(
                        choices=[
                            ("grade", "Оценка"),
                            ("attendance", "Посещаемость"),
                            ("lesson", "Занятие"),
                        ],
                        max_length=20,
                        verbose_name="объект изменения",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("create", "Создание"),
                            ("update", "Изменение"),
                            ("delete", "Удаление"),
                        ],
                        max_length=20,
                        verbose_name="действие",
                    ),
                ),
                (
                    "old_value",
                    models.CharField(
                        blank=True,
                        max_length=250,
                        verbose_name="было",
                    ),
                ),
                (
                    "new_value",
                    models.CharField(
                        blank=True,
                        max_length=250,
                        verbose_name="стало",
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        max_length=500,
                        verbose_name="основание",
                    ),
                ),
                (
                    "comment",
                    models.TextField(
                        blank=True,
                        verbose_name="комментарий",
                    ),
                ),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="change_logs",
                        to="journal.teachingassignment",
                        verbose_name="назначение дисциплины",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="journal_change_logs",
                        to="journal.student",
                        verbose_name="студент",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="journal_change_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "изменение журнала",
                "verbose_name_plural": "журнал изменений",
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
