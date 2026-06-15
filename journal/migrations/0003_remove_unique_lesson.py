from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0002_assignment_period"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="lesson",
            name="unique_lesson",
        ),
    ]
