from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0005_journal_change_log"),
    ]

    operations = [
        migrations.CreateModel(
            name="CollegeInformation",
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
                    "name",
                    models.CharField(
                        max_length=300,
                        verbose_name="название учебного заведения",
                    ),
                ),
                (
                    "address",
                    models.CharField(
                        blank=True,
                        max_length=500,
                        verbose_name="адрес",
                    ),
                ),
                (
                    "inn",
                    models.CharField(
                        blank=True,
                        max_length=12,
                        verbose_name="ИНН",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        max_length=254,
                        verbose_name="адрес электронной почты",
                    ),
                ),
            ],
            options={
                "verbose_name": "сведения о колледже",
                "verbose_name_plural": "сведения о колледже",
            },
        ),
    ]
