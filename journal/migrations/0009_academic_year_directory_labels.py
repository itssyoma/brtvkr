from django.db import migrations


def create_existing_academic_years(apps, schema_editor):
    TeachingAssignment = apps.get_model("journal", "TeachingAssignment")
    AcademicYearArchive = apps.get_model(
        "journal",
        "AcademicYearArchive",
    )
    years = (
        TeachingAssignment.objects.exclude(academic_year="")
        .values_list("academic_year", flat=True)
        .distinct()
    )
    for academic_year in years:
        AcademicYearArchive.objects.get_or_create(
            academic_year=academic_year
        )


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0008_expand_assignment_semesters"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="collegeinformation",
            options={
                "verbose_name": "сведения об образовательной организации",
                "verbose_name_plural": (
                    "сведения об образовательной организации"
                ),
            },
        ),
        migrations.AlterModelOptions(
            name="academicyeararchive",
            options={
                "ordering": ["-academic_year"],
                "verbose_name": "учебный год",
                "verbose_name_plural": "учебные годы",
            },
        ),
        migrations.RunPython(
            create_existing_academic_years,
            migrations.RunPython.noop,
        ),
    ]
