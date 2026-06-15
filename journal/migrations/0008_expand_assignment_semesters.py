from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0007_academic_year_archive"),
    ]

    operations = [
        migrations.AlterField(
            model_name="teachingassignment",
            name="semester",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "1 семестр"),
                    (2, "2 семестр"),
                    (3, "3 семестр"),
                    (4, "4 семестр"),
                    (5, "5 семестр"),
                    (6, "6 семестр"),
                    (7, "7 семестр"),
                    (8, "8 семестр"),
                ],
                default=1,
                verbose_name="семестр",
            ),
        ),
    ]
