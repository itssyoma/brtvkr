import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0003_remove_unique_lesson"),
    ]

    operations = [
        migrations.CreateModel(
            name="CurriculumPlanItem",
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
                    "sequence",
                    models.PositiveIntegerField(verbose_name="номер по порядку"),
                ),
                (
                    "planned_date",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="плановая дата",
                    ),
                ),
                (
                    "topic",
                    models.CharField(
                        max_length=500,
                        verbose_name="тема занятия",
                    ),
                ),
                (
                    "lesson_type",
                    models.CharField(
                        choices=[
                            ("lecture", "Лекция"),
                            ("practice", "Практическое занятие"),
                            ("laboratory", "Лабораторная работа"),
                            ("self_study", "Самостоятельная работа"),
                            ("consultation", "Консультация"),
                            ("exam", "Экзамен"),
                            ("credit", "Зачёт"),
                            ("diff_credit", "Дифференцированный зачёт"),
                            ("semester_grade", "Семестровая оценка"),
                        ],
                        default="lecture",
                        max_length=20,
                        verbose_name="вид занятия",
                    ),
                ),
                (
                    "hours",
                    models.DecimalField(
                        decimal_places=2,
                        default=1,
                        max_digits=5,
                        verbose_name="количество часов",
                    ),
                ),
                (
                    "literature",
                    models.CharField(
                        blank=True,
                        max_length=500,
                        verbose_name="литература",
                    ),
                ),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="curriculum_items",
                        to="journal.teachingassignment",
                        verbose_name="назначение дисциплины",
                    ),
                ),
            ],
            options={
                "verbose_name": "тема КТП",
                "verbose_name_plural": "темы КТП",
                "ordering": ["sequence", "id"],
            },
        ),
        migrations.AddField(
            model_name="lesson",
            name="curriculum_item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="lessons",
                to="journal.curriculumplanitem",
                verbose_name="тема КТП",
            ),
        ),
        migrations.AddField(
            model_name="lesson",
            name="grading_scheme",
            field=models.CharField(
                choices=[
                    ("numeric", "Оценка 2–5"),
                    ("pass_fail", "Зачёт / незачёт"),
                    ("none", "Без оценки"),
                ],
                default="numeric",
                max_length=20,
                verbose_name="система оценивания",
            ),
        ),
        migrations.AddField(
            model_name="lesson",
            name="lesson_type",
            field=models.CharField(
                choices=[
                    ("lecture", "Лекция"),
                    ("practice", "Практическое занятие"),
                    ("laboratory", "Лабораторная работа"),
                    ("self_study", "Самостоятельная работа"),
                    ("consultation", "Консультация"),
                    ("exam", "Экзамен"),
                    ("credit", "Зачёт"),
                    ("diff_credit", "Дифференцированный зачёт"),
                    ("semester_grade", "Семестровая оценка"),
                ],
                default="lecture",
                max_length=20,
                verbose_name="вид занятия",
            ),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="topic",
            field=models.CharField(
                max_length=500,
                verbose_name="тема занятия",
            ),
        ),
        migrations.AlterField(
            model_name="grade",
            name="value",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(2),
                    django.core.validators.MaxValueValidator(5),
                ],
                verbose_name="оценка",
            ),
        ),
        migrations.AddField(
            model_name="grade",
            name="pass_result",
            field=models.CharField(
                blank=True,
                choices=[("passed", "Зачёт"), ("failed", "Незачёт")],
                max_length=10,
                verbose_name="результат зачёта",
            ),
        ),
        migrations.AddConstraint(
            model_name="curriculumplanitem",
            constraint=models.UniqueConstraint(
                fields=("assignment", "sequence"),
                name="unique_curriculum_sequence",
            ),
        ),
    ]
