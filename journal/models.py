from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def user_full_name(user):
    if user is None:
        return ""
    try:
        middle_name = user.journal_profile.middle_name
    except UserProfile.DoesNotExist:
        middle_name = ""
    full_name = " ".join(
        part
        for part in [
            user.last_name,
            user.first_name,
            middle_name,
        ]
        if part
    )
    return full_name or user.get_username()


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="пользователь",
        on_delete=models.CASCADE,
        related_name="journal_profile",
    )
    middle_name = models.CharField("отчество", max_length=150, blank=True)

    class Meta:
        verbose_name = "дополнительные сведения пользователя"
        verbose_name_plural = "дополнительные сведения пользователей"

    def __str__(self):
        return user_full_name(self.user)


class CollegeInformation(models.Model):
    name = models.CharField("название учебного заведения", max_length=300)
    address = models.CharField("адрес", max_length=500, blank=True)
    inn = models.CharField("ИНН", max_length=12, blank=True)
    email = models.EmailField("адрес электронной почты", blank=True)

    class Meta:
        verbose_name = "сведения об образовательной организации"
        verbose_name_plural = "сведения об образовательной организации"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk and CollegeInformation.objects.exists():
            raise ValidationError(
                "В системе может быть только одна карточка колледжа."
            )
        super().save(*args, **kwargs)

    @classmethod
    def get_current(cls):
        return cls.objects.first()


class AcademicYearArchive(models.Model):
    academic_year = models.CharField(
        "учебный год",
        max_length=9,
        unique=True,
        help_text="Например: 2025/2026",
    )
    order_number = models.CharField(
        "номер приказа",
        max_length=100,
        blank=True,
    )
    order_date = models.DateField("дата приказа", null=True, blank=True)
    comment = models.TextField("комментарий", blank=True)
    is_locked = models.BooleanField("архив закрыт", default=False)
    archived_at = models.DateTimeField(
        "дата архивирования",
        null=True,
        blank=True,
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="архивировал",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_academic_year_archives",
    )
    archive_filename = models.CharField(
        "имя архивного файла",
        max_length=255,
        blank=True,
    )
    archive_data = models.BinaryField(
        "архивный файл",
        null=True,
        blank=True,
        editable=False,
    )
    checksum = models.CharField(
        "контрольная сумма SHA-256",
        max_length=64,
        blank=True,
        editable=False,
    )
    reopened_at = models.DateTimeField(
        "дата повторного открытия",
        null=True,
        blank=True,
    )
    reopened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="повторно открыл",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reopened_academic_year_archives",
    )
    reopen_reason = models.TextField(
        "причина повторного открытия",
        blank=True,
    )

    class Meta:
        verbose_name = "учебный год"
        verbose_name_plural = "учебные годы"
        ordering = ["-academic_year"]

    def __str__(self):
        status = "закрыт" if self.is_locked else "открыт"
        return f"{self.academic_year} — {status}"

    @classmethod
    def is_year_locked(cls, academic_year):
        return cls.objects.filter(
            academic_year=academic_year,
            is_locked=True,
        ).exists()


class AcademicYearArchiveEvent(models.Model):
    class Action(models.TextChoices):
        CLOSE = "close", "Закрытие"
        REOPEN = "reopen", "Повторное открытие"

    archive = models.ForeignKey(
        AcademicYearArchive,
        verbose_name="архив учебного года",
        on_delete=models.PROTECT,
        related_name="events",
    )
    created_at = models.DateTimeField("дата и время", auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="пользователь",
        on_delete=models.PROTECT,
        related_name="academic_year_archive_events",
    )
    action = models.CharField(
        "действие",
        max_length=10,
        choices=Action.choices,
    )
    reason = models.TextField("основание")
    checksum = models.CharField(
        "контрольная сумма SHA-256",
        max_length=64,
        blank=True,
    )

    class Meta:
        verbose_name = "событие архива"
        verbose_name_plural = "история архива"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return (
            f"{self.archive.academic_year}: "
            f"{self.get_action_display()} — {self.created_at:%d.%m.%Y %H:%M}"
        )


class StudyGroup(models.Model):
    name = models.CharField("название", max_length=30, unique=True)
    admission_year = models.PositiveSmallIntegerField("год поступления")
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="куратор",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="curated_groups",
    )

    class Meta:
        verbose_name = "учебная группа"
        verbose_name_plural = "учебные группы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Student(models.Model):
    group = models.ForeignKey(
        StudyGroup,
        verbose_name="группа",
        on_delete=models.PROTECT,
        related_name="students",
    )
    last_name = models.CharField("фамилия", max_length=100)
    first_name = models.CharField("имя", max_length=100)
    middle_name = models.CharField("отчество", max_length=100, blank=True)
    student_card_number = models.CharField(
        "номер студенческого билета",
        max_length=30,
        unique=True,
    )
    is_active = models.BooleanField("обучается", default=True)

    class Meta:
        verbose_name = "студент"
        verbose_name_plural = "студенты"
        ordering = ["last_name", "first_name", "middle_name"]

    def __str__(self):
        return " ".join(
            part for part in [self.last_name, self.first_name, self.middle_name] if part
        )


class Subject(models.Model):
    name = models.CharField("название", max_length=200, unique=True)
    short_name = models.CharField("сокращённое название", max_length=30, blank=True)

    class Meta:
        verbose_name = "дисциплина"
        verbose_name_plural = "дисциплины"
        ordering = ["name"]

    def __str__(self):
        return self.name


class TeachingAssignment(models.Model):
    class Semester(models.IntegerChoices):
        FIRST = 1, "1 семестр"
        SECOND = 2, "2 семестр"
        THIRD = 3, "3 семестр"
        FOURTH = 4, "4 семестр"
        FIFTH = 5, "5 семестр"
        SIXTH = 6, "6 семестр"
        SEVENTH = 7, "7 семестр"
        EIGHTH = 8, "8 семестр"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="преподаватель",
        on_delete=models.PROTECT,
        related_name="teaching_assignments",
    )
    group = models.ForeignKey(
        StudyGroup,
        verbose_name="группа",
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
    )
    subject = models.ForeignKey(
        Subject,
        verbose_name="дисциплина",
        on_delete=models.PROTECT,
        related_name="teaching_assignments",
    )
    academic_year = models.CharField(
        "учебный год",
        max_length=9,
        default="2025/2026",
        help_text="Например: 2025/2026",
    )
    semester = models.PositiveSmallIntegerField(
        "семестр",
        choices=Semester.choices,
        default=Semester.FIRST,
    )

    class Meta:
        verbose_name = "назначение дисциплины"
        verbose_name_plural = "назначения дисциплин"
        ordering = [
            "-academic_year",
            "semester",
            "group__name",
            "subject__name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "group",
                    "subject",
                    "academic_year",
                    "semester",
                ],
                name="unique_teaching_assignment",
            )
        ]

    def __str__(self):
        return (
            f"{self.subject} — {self.group}, "
            f"{self.academic_year}, {self.get_semester_display()} "
            f"({user_full_name(self.teacher)})"
        )

    def clean(self):
        if (
            self.academic_year
            and not AcademicYearArchive.objects.filter(
                academic_year=self.academic_year
            ).exists()
        ):
            raise ValidationError(
                {
                    "academic_year": (
                        "Выберите учебный год, созданный в разделе "
                        "«Учебные годы»."
                    )
                }
            )
        years_to_check = {self.academic_year}
        if self.pk:
            previous_year = (
                TeachingAssignment.objects.filter(pk=self.pk)
                .values_list("academic_year", flat=True)
                .first()
            )
            if previous_year:
                years_to_check.add(previous_year)
        if any(
            AcademicYearArchive.is_year_locked(year)
            for year in years_to_check
        ):
            raise ValidationError(
                "Нельзя изменять назначение дисциплины архивного учебного года."
            )


class LessonType(models.TextChoices):
    LECTURE = "lecture", "Лекция"
    PRACTICE = "practice", "Практическое занятие"
    LABORATORY = "laboratory", "Лабораторная работа"
    SELF_STUDY = "self_study", "Самостоятельная работа"
    CONSULTATION = "consultation", "Консультация"
    EXAM = "exam", "Экзамен"
    CREDIT = "credit", "Зачёт"
    DIFFERENTIATED_CREDIT = "diff_credit", "Дифференцированный зачёт"
    SEMESTER_GRADE = "semester_grade", "Семестровая оценка"


class GradingScheme(models.TextChoices):
    NUMERIC = "numeric", "Оценка 2–5"
    PASS_FAIL = "pass_fail", "Зачёт / незачёт"
    NONE = "none", "Без оценки"


class CurriculumPlanItem(models.Model):
    assignment = models.ForeignKey(
        TeachingAssignment,
        verbose_name="назначение дисциплины",
        on_delete=models.CASCADE,
        related_name="curriculum_items",
    )
    sequence = models.PositiveIntegerField("номер по порядку")
    planned_date = models.DateField("плановая дата", null=True, blank=True)
    topic = models.CharField("тема занятия", max_length=500)
    lesson_type = models.CharField(
        "вид занятия",
        max_length=20,
        choices=LessonType.choices,
        default=LessonType.LECTURE,
    )
    hours = models.DecimalField(
        "количество часов",
        max_digits=5,
        decimal_places=2,
        default=1,
    )
    literature = models.CharField("литература", max_length=500, blank=True)

    class Meta:
        verbose_name = "тема КТП"
        verbose_name_plural = "темы КТП"
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "sequence"],
                name="unique_curriculum_sequence",
            )
        ]

    def __str__(self):
        return f"{self.sequence}. {self.topic}"

    def clean(self):
        if (
            self.assignment_id
            and AcademicYearArchive.is_year_locked(
                self.assignment.academic_year
            )
        ):
            raise ValidationError("КТП архивного учебного года изменять нельзя.")


class Lesson(models.Model):
    assignment = models.ForeignKey(
        TeachingAssignment,
        verbose_name="назначение дисциплины",
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    date = models.DateField("дата занятия")
    topic = models.CharField("тема занятия", max_length=500)
    curriculum_item = models.ForeignKey(
        CurriculumPlanItem,
        verbose_name="тема КТП",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
    )
    lesson_type = models.CharField(
        "вид занятия",
        max_length=20,
        choices=LessonType.choices,
        default=LessonType.LECTURE,
    )
    grading_scheme = models.CharField(
        "система оценивания",
        max_length=20,
        choices=GradingScheme.choices,
        default=GradingScheme.NUMERIC,
    )

    class Meta:
        verbose_name = "занятие"
        verbose_name_plural = "занятия"
        ordering = ["-date", "assignment"]

    def __str__(self):
        return f"{self.date:%d.%m.%Y}: {self.topic}"

    def clean(self):
        if (
            self.assignment_id
            and AcademicYearArchive.is_year_locked(
                self.assignment.academic_year
            )
        ):
            raise ValidationError(
                "Занятия архивного учебного года изменять нельзя."
            )


class Grade(models.Model):
    class PassResult(models.TextChoices):
        PASSED = "passed", "Зачёт"
        FAILED = "failed", "Незачёт"

    student = models.ForeignKey(
        Student,
        verbose_name="студент",
        on_delete=models.CASCADE,
        related_name="grades",
    )
    lesson = models.ForeignKey(
        Lesson,
        verbose_name="занятие",
        on_delete=models.CASCADE,
        related_name="grades",
    )
    value = models.PositiveSmallIntegerField(
        "оценка",
        validators=[MinValueValidator(2), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    pass_result = models.CharField(
        "результат зачёта",
        max_length=10,
        choices=PassResult.choices,
        blank=True,
    )
    comment = models.CharField("комментарий", max_length=250, blank=True)

    class Meta:
        verbose_name = "оценка"
        verbose_name_plural = "оценки"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "lesson"],
                name="unique_grade_per_lesson",
            )
        ]

    def __str__(self):
        result = self.get_pass_result_display() if self.pass_result else self.value
        return f"{self.student}: {result}"

    def clean(self):
        if (
            self.lesson_id
            and AcademicYearArchive.is_year_locked(
                self.lesson.assignment.academic_year
            )
        ):
            raise ValidationError(
                "Оценки архивного учебного года изменять нельзя."
            )
        if (
            self.student_id
            and self.lesson_id
            and self.student.group_id != self.lesson.assignment.group_id
        ):
            raise ValidationError(
                "Оценку можно выставить только студенту группы этого занятия."
            )
        if self.lesson_id:
            if self.lesson.grading_scheme == GradingScheme.NUMERIC:
                if self.value is None or self.pass_result:
                    raise ValidationError("Для занятия требуется оценка от 2 до 5.")
            elif self.lesson.grading_scheme == GradingScheme.PASS_FAIL:
                if not self.pass_result or self.value is not None:
                    raise ValidationError(
                        "Для занятия требуется результат зачёт/незачёт."
                    )
            elif self.value is not None or self.pass_result:
                raise ValidationError("Для этого занятия оценивание не предусмотрено.")


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Присутствовал"
        ABSENT = "absent", "Отсутствовал"
        EXCUSED = "excused", "Уважительная причина"
        LATE = "late", "Опоздал"

    student = models.ForeignKey(
        Student,
        verbose_name="студент",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    lesson = models.ForeignKey(
        Lesson,
        verbose_name="занятие",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    status = models.CharField(
        "статус",
        max_length=10,
        choices=Status.choices,
        default=Status.PRESENT,
    )
    comment = models.CharField("комментарий", max_length=250, blank=True)

    class Meta:
        verbose_name = "посещаемость"
        verbose_name_plural = "посещаемость"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "lesson"],
                name="unique_attendance_per_lesson",
            )
        ]

    def __str__(self):
        return f"{self.student}: {self.get_status_display()}"

    def clean(self):
        if (
            self.lesson_id
            and AcademicYearArchive.is_year_locked(
                self.lesson.assignment.academic_year
            )
        ):
            raise ValidationError(
                "Посещаемость архивного учебного года изменять нельзя."
            )
        if (
            self.student_id
            and self.lesson_id
            and self.student.group_id != self.lesson.assignment.group_id
        ):
            raise ValidationError(
                "Посещаемость можно отметить только студенту группы этого занятия."
            )


class JournalChangeLog(models.Model):
    class EntityType(models.TextChoices):
        GRADE = "grade", "Оценка"
        ATTENDANCE = "attendance", "Посещаемость"
        LESSON = "lesson", "Занятие"

    class Action(models.TextChoices):
        CREATE = "create", "Создание"
        UPDATE = "update", "Изменение"
        DELETE = "delete", "Удаление"

    created_at = models.DateTimeField("дата и время", auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="пользователь",
        on_delete=models.PROTECT,
        related_name="journal_change_logs",
    )
    assignment = models.ForeignKey(
        TeachingAssignment,
        verbose_name="назначение дисциплины",
        on_delete=models.PROTECT,
        related_name="change_logs",
    )
    lesson_date = models.DateField("дата занятия")
    lesson_topic = models.CharField("тема занятия", max_length=500)
    student = models.ForeignKey(
        Student,
        verbose_name="студент",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="journal_change_logs",
    )
    student_name = models.CharField("ФИО студента", max_length=320, blank=True)
    entity_type = models.CharField(
        "объект изменения",
        max_length=20,
        choices=EntityType.choices,
    )
    action = models.CharField(
        "действие",
        max_length=20,
        choices=Action.choices,
    )
    old_value = models.CharField("было", max_length=250, blank=True)
    new_value = models.CharField("стало", max_length=250, blank=True)
    reason = models.CharField("основание", max_length=500)
    comment = models.TextField("комментарий", blank=True)

    class Meta:
        verbose_name = "изменение журнала"
        verbose_name_plural = "журнал изменений"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return (
            f"{self.created_at:%d.%m.%Y %H:%M}: "
            f"{self.get_entity_type_display()} — {self.student_name or 'занятие'}"
        )
