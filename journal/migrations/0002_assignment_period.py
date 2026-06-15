import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="teachingassignment",
            name="unique_teaching_assignment",
        ),
        migrations.AlterModelOptions(
            name="teachingassignment",
            options={
                "ordering": [
                    "-academic_year",
                    "semester",
                    "group__name",
                    "subject__name",
                ],
                "verbose_name": "назначение дисциплины",
                "verbose_name_plural": "назначения дисциплин",
            },
        ),
        migrations.AddField(
            model_name="teachingassignment",
            name="academic_year",
            field=models.CharField(
                default="2025/2026",
                help_text="Например: 2025/2026",
                max_length=9,
                verbose_name="учебный год",
            ),
        ),
        migrations.AddField(
            model_name="teachingassignment",
            name="semester",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "1 семестр"), (2, "2 семестр")],
                default=1,
                verbose_name="семестр",
            ),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="assignment",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lessons",
                to="journal.teachingassignment",
                verbose_name="назначение дисциплины",
            ),
        ),
        migrations.AddConstraint(
            model_name="teachingassignment",
            constraint=models.UniqueConstraint(
                fields=(
                    "group",
                    "subject",
                    "academic_year",
                    "semester",
                ),
                name="unique_teaching_assignment",
            ),
        ),
    ]
