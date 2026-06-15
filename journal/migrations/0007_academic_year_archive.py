import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("journal", "0006_college_information"),
    ]

    operations = [
        migrations.CreateModel(
            name="AcademicYearArchive",
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
                    "academic_year",
                    models.CharField(
                        help_text="Например: 2025/2026",
                        max_length=9,
                        unique=True,
                        verbose_name="учебный год",
                    ),
                ),
                (
                    "order_number",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        verbose_name="номер приказа",
                    ),
                ),
                (
                    "order_date",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="дата приказа",
                    ),
                ),
                (
                    "comment",
                    models.TextField(blank=True, verbose_name="комментарий"),
                ),
                (
                    "is_locked",
                    models.BooleanField(
                        default=False,
                        verbose_name="архив закрыт",
                    ),
                ),
                (
                    "archived_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="дата архивирования",
                    ),
                ),
                (
                    "archive_filename",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        verbose_name="имя архивного файла",
                    ),
                ),
                (
                    "archive_data",
                    models.BinaryField(
                        blank=True,
                        editable=False,
                        null=True,
                        verbose_name="архивный файл",
                    ),
                ),
                (
                    "checksum",
                    models.CharField(
                        blank=True,
                        editable=False,
                        max_length=64,
                        verbose_name="контрольная сумма SHA-256",
                    ),
                ),
                (
                    "reopened_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="дата повторного открытия",
                    ),
                ),
                (
                    "reopen_reason",
                    models.TextField(
                        blank=True,
                        verbose_name="причина повторного открытия",
                    ),
                ),
                (
                    "archived_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="closed_academic_year_archives",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="архивировал",
                    ),
                ),
                (
                    "reopened_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reopened_academic_year_archives",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="повторно открыл",
                    ),
                ),
            ],
            options={
                "verbose_name": "архив учебного года",
                "verbose_name_plural": "архив учебных лет",
                "ordering": ["-academic_year"],
            },
        ),
        migrations.CreateModel(
            name="AcademicYearArchiveEvent",
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
                    "action",
                    models.CharField(
                        choices=[
                            ("close", "Закрытие"),
                            ("reopen", "Повторное открытие"),
                        ],
                        max_length=10,
                        verbose_name="действие",
                    ),
                ),
                (
                    "reason",
                    models.TextField(verbose_name="основание"),
                ),
                (
                    "checksum",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        verbose_name="контрольная сумма SHA-256",
                    ),
                ),
                (
                    "archive",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="events",
                        to="journal.academicyeararchive",
                        verbose_name="архив учебного года",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="academic_year_archive_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "событие архива",
                "verbose_name_plural": "история архива",
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
