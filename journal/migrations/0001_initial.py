# Generated for the initial electronic journal data model.
import django.db.models.deletion
import django.core.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudyGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=30, unique=True, verbose_name="название")),
                ("admission_year", models.PositiveSmallIntegerField(verbose_name="год поступления")),
                ("curator", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="curated_groups", to=settings.AUTH_USER_MODEL, verbose_name="куратор")),
            ],
            options={
                "verbose_name": "учебная группа",
                "verbose_name_plural": "учебные группы",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Subject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, unique=True, verbose_name="название")),
                ("short_name", models.CharField(blank=True, max_length=30, verbose_name="сокращённое название")),
            ],
            options={
                "verbose_name": "дисциплина",
                "verbose_name_plural": "дисциплины",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Student",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_name", models.CharField(max_length=100, verbose_name="фамилия")),
                ("first_name", models.CharField(max_length=100, verbose_name="имя")),
                ("middle_name", models.CharField(blank=True, max_length=100, verbose_name="отчество")),
                ("student_card_number", models.CharField(max_length=30, unique=True, verbose_name="номер студенческого билета")),
                ("is_active", models.BooleanField(default=True, verbose_name="обучается")),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="students", to="journal.studygroup", verbose_name="группа")),
            ],
            options={
                "verbose_name": "студент",
                "verbose_name_plural": "студенты",
                "ordering": ["last_name", "first_name", "middle_name"],
            },
        ),
        migrations.CreateModel(
            name="TeachingAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teaching_assignments", to="journal.studygroup", verbose_name="группа")),
                ("subject", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teaching_assignments", to="journal.subject", verbose_name="дисциплина")),
                ("teacher", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teaching_assignments", to=settings.AUTH_USER_MODEL, verbose_name="преподаватель")),
            ],
            options={
                "verbose_name": "учебная нагрузка",
                "verbose_name_plural": "учебная нагрузка",
            },
        ),
        migrations.CreateModel(
            name="Lesson",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(verbose_name="дата занятия")),
                ("topic", models.CharField(max_length=250, verbose_name="тема занятия")),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lessons", to="journal.teachingassignment", verbose_name="учебная нагрузка")),
            ],
            options={
                "verbose_name": "занятие",
                "verbose_name_plural": "занятия",
                "ordering": ["-date", "assignment"],
            },
        ),
        migrations.CreateModel(
            name="Grade",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(2), django.core.validators.MaxValueValidator(5)], verbose_name="оценка")),
                ("comment", models.CharField(blank=True, max_length=250, verbose_name="комментарий")),
                ("lesson", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="grades", to="journal.lesson", verbose_name="занятие")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="grades", to="journal.student", verbose_name="студент")),
            ],
            options={
                "verbose_name": "оценка",
                "verbose_name_plural": "оценки",
            },
        ),
        migrations.CreateModel(
            name="Attendance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("present", "Присутствовал"), ("absent", "Отсутствовал"), ("excused", "Уважительная причина"), ("late", "Опоздал")], default="present", max_length=10, verbose_name="статус")),
                ("comment", models.CharField(blank=True, max_length=250, verbose_name="комментарий")),
                ("lesson", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attendance_records", to="journal.lesson", verbose_name="занятие")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attendance_records", to="journal.student", verbose_name="студент")),
            ],
            options={
                "verbose_name": "посещаемость",
                "verbose_name_plural": "посещаемость",
            },
        ),
        migrations.AddConstraint(
            model_name="teachingassignment",
            constraint=models.UniqueConstraint(fields=("teacher", "group", "subject"), name="unique_teaching_assignment"),
        ),
        migrations.AddConstraint(
            model_name="lesson",
            constraint=models.UniqueConstraint(fields=("assignment", "date", "topic"), name="unique_lesson"),
        ),
        migrations.AddConstraint(
            model_name="grade",
            constraint=models.UniqueConstraint(fields=("student", "lesson"), name="unique_grade_per_lesson"),
        ),
        migrations.AddConstraint(
            model_name="attendance",
            constraint=models.UniqueConstraint(fields=("student", "lesson"), name="unique_attendance_per_lesson"),
        ),
    ]
