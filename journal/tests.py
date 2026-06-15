from datetime import date
from io import BytesIO
import zipfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import (
    AcademicYearArchive,
    AcademicYearArchiveEvent,
    Attendance,
    CollegeInformation,
    CurriculumPlanItem,
    Grade,
    GradingScheme,
    JournalChangeLog,
    Lesson,
    LessonType,
    Student,
    StudyGroup,
    Subject,
    TeachingAssignment,
    UserProfile,
    user_full_name,
)
from .reports import _student_summary_metrics
from .reports import _build_csv


class DefaultUserGroupsTests(TestCase):
    def test_default_user_groups_exist(self):
        self.assertEqual(
            set(
                Group.objects.filter(
                    name__in={
                        "Администраторы",
                        "Учебная часть",
                        "Преподаватели",
                        "Кураторы",
                        "Аудиторы",
                    }
                ).values_list("name", flat=True)
            ),
            {
                "Администраторы",
                "Учебная часть",
                "Преподаватели",
                "Кураторы",
                "Аудиторы",
            },
        )

    def test_default_groups_have_role_permissions(self):
        administrators = Group.objects.get(name="Администраторы")
        academic_office = Group.objects.get(name="Учебная часть")
        teachers = Group.objects.get(name="Преподаватели")
        curators = Group.objects.get(name="Кураторы")
        auditors = Group.objects.get(name="Аудиторы")

        self.assertTrue(
            administrators.permissions.filter(
                content_type__app_label="auth",
                codename="change_user",
            ).exists()
        )
        self.assertTrue(
            academic_office.permissions.filter(
                content_type__app_label="journal",
                codename="change_student",
            ).exists()
        )
        self.assertFalse(
            academic_office.permissions.filter(
                content_type__app_label="journal",
                codename="change_grade",
            ).exists()
        )
        self.assertTrue(
            teachers.permissions.filter(
                content_type__app_label="journal",
                codename="view_teachingassignment",
            ).exists()
        )
        self.assertTrue(
            curators.permissions.filter(
                content_type__app_label="journal",
                codename="view_grade",
            ).exists()
        )
        self.assertTrue(
            auditors.permissions.filter(
                content_type__app_label="journal",
                codename="view_journalchangelog",
            ).exists()
        )
        self.assertFalse(
            auditors.permissions.filter(
                codename__startswith="change_",
            ).exists()
        )

    def test_administrative_group_enables_staff_status(self):
        user = get_user_model().objects.create_user(
            username="academic-office",
            password="test-password",
        )

        user.groups.add(Group.objects.get(name="Учебная часть"))
        user.refresh_from_db()

        self.assertTrue(user.is_staff)


class SecurityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="security-user",
            password="test-password",
        )
        self.group = StudyGroup.objects.create(
            name="SEC-01",
            admission_year=2025,
        )
        self.subject = Subject.objects.create(
            name="<script>alert('xss')</script>",
        )
        self.assignment = TeachingAssignment.objects.create(
            teacher=self.user,
            group=self.group,
            subject=self.subject,
            academic_year="2025/2026",
            semester=TeachingAssignment.Semester.FIRST,
        )

    def test_post_request_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        response = client.post(
            reverse(
                "journal:assignment_detail",
                args=[self.assignment.pk],
            ),
            {
                "action": "create_lesson",
                "date": date.today().isoformat(),
                "topic": "Несанкционированное занятие",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Lesson.objects.exists())

    def test_login_rejects_sql_injection_payload(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "' OR 1=1 --",
                "password": "irrelevant",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_user_content_is_html_escaped(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("journal:dashboard"))

        self.assertContains(
            response,
            "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;",
        )
        self.assertNotContains(response, "<script>alert('xss')</script>")

    @override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True)
    def test_security_headers_are_added(self):
        response = self.client.get(reverse("journal:home"))

        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")


class TeacherJournalTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.teacher = user_model.objects.create_user(
            username="teacher",
            password="test-password",
        )
        self.other_teacher = user_model.objects.create_user(
            username="other",
            password="test-password",
        )
        self.curator = user_model.objects.create_user(
            username="curator",
            password="test-password",
        )
        self.auditor = user_model.objects.create_user(
            username="auditor",
            password="test-password",
        )
        self.auditor.groups.add(Group.objects.get(name="Аудиторы"))
        self.group = StudyGroup.objects.create(
            name="ИСП-21",
            admission_year=2024,
            curator=self.curator,
        )
        self.student = Student.objects.create(
            group=self.group,
            last_name="Иванов",
            first_name="Иван",
            student_card_number="001",
        )
        self.subject = Subject.objects.create(name="Программирование")
        self.assignment = TeachingAssignment.objects.create(
            teacher=self.teacher,
            group=self.group,
            subject=self.subject,
            academic_year="2025/2026",
            semester=TeachingAssignment.Semester.SECOND,
        )
        self.lesson = Lesson.objects.create(
            assignment=self.assignment,
            date=date.today(),
            topic="Основы Python",
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("journal:dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('journal:dashboard')}",
        )

    def test_teacher_sees_only_own_assignments(self):
        self.client.login(username="teacher", password="test-password")

        response = self.client.get(reverse("journal:dashboard"))

        self.assertContains(response, "Программирование")

    def test_curator_can_view_assignments_for_curated_group(self):
        self.client.login(username="curator", password="test-password")

        dashboard_response = self.client.get(reverse("journal:dashboard"))
        journal_response = self.client.get(
            reverse("journal:assignment_detail", args=[self.assignment.pk])
        )

        self.assertContains(
            dashboard_response,
            "Дисциплины в курируемых группах",
        )
        self.assertContains(dashboard_response, "Программирование")
        self.assertContains(journal_response, "Режим просмотра")
        self.assertNotContains(journal_response, "Изменить")
        self.assertNotContains(journal_response, "Новое занятие")

    def test_curator_cannot_change_assignment_or_lesson(self):
        self.client.login(username="curator", password="test-password")

        edit_response = self.client.get(
            reverse("journal:assignment_detail", args=[self.assignment.pk]),
            {"edit": "1"},
        )
        assignment_post_response = self.client.post(
            reverse("journal:assignment_detail", args=[self.assignment.pk]),
            {"action": "save_journal"},
        )
        lesson_post_response = self.client.post(
            reverse("journal:lesson_detail", args=[self.lesson.pk]),
            {
                f"grade_{self.student.pk}": "5",
                f"attendance_{self.student.pk}": Attendance.Status.LATE,
            },
        )

        self.assertNotContains(edit_response, f"name=\"grade_{self.student.pk}_")
        self.assertEqual(assignment_post_response.status_code, 403)
        self.assertEqual(lesson_post_response.status_code, 403)
        self.assertFalse(Grade.objects.exists())
        self.assertFalse(Attendance.objects.exists())

    def test_auditor_can_view_all_journals_but_cannot_edit(self):
        self.client.login(username="auditor", password="test-password")

        dashboard_response = self.client.get(reverse("journal:dashboard"))
        journal_response = self.client.get(
            reverse("journal:assignment_detail", args=[self.assignment.pk]),
            {"edit": "1"},
        )
        post_response = self.client.post(
            reverse("journal:assignment_detail", args=[self.assignment.pk]),
            {"action": "save_journal"},
        )

        self.assertContains(dashboard_response, "Все журналы колледжа")
        self.assertContains(dashboard_response, "Программирование")
        self.assertContains(journal_response, "Режим просмотра")
        self.assertNotContains(journal_response, "Изменить")
        self.assertEqual(post_response.status_code, 403)

    def test_other_teacher_cannot_open_lesson(self):
        self.client.login(username="other", password="test-password")

        response = self.client.get(
            reverse("journal:lesson_detail", args=[self.lesson.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_teacher_can_save_grade_and_attendance(self):
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse("journal:lesson_detail", args=[self.lesson.pk]),
            {
                f"grade_{self.student.pk}": "5",
                f"attendance_{self.student.pk}": Attendance.Status.LATE,
                "change_reason": "Результаты текущего контроля",
            },
        )

        self.assertRedirects(
            response,
            reverse("journal:lesson_detail", args=[self.lesson.pk]),
        )
        self.assertEqual(
            Grade.objects.get(student=self.student, lesson=self.lesson).value,
            5,
        )
        self.assertEqual(
            Attendance.objects.get(
                student=self.student,
                lesson=self.lesson,
            ).status,
            Attendance.Status.LATE,
        )

    def test_assignment_page_shows_summary_metrics(self):
        Grade.objects.create(
            student=self.student,
            lesson=self.lesson,
            value=5,
        )
        Attendance.objects.create(
            student=self.student,
            lesson=self.lesson,
            status=Attendance.Status.ABSENT,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.get(
            reverse("journal:assignment_detail", args=[self.assignment.pk])
        )

        self.assertContains(response, "Сводный журнал")
        self.assertContains(response, "5,0")
        self.assertContains(response, "Н")

    def test_assignment_edit_mode_shows_grade_fields(self):
        self.client.login(username="teacher", password="test-password")

        response = self.client.get(
            reverse("journal:assignment_detail", args=[self.assignment.pk]),
            {"edit": "1"},
        )

        field_name = f"grade_{self.student.pk}_{self.lesson.pk}"
        attendance_field = (
            f"attendance_{self.student.pk}_{self.lesson.pk}"
        )
        self.assertContains(response, "Сохранить вручную")
        self.assertContains(response, f'name="{field_name}"')
        self.assertContains(response, f'name="{attendance_field}"')
        self.assertContains(
            response,
            'value="Исправление технической ошибки" selected',
        )
        self.assertContains(
            response,
            "Исправление показателя успеваемости студента в лучшую сторону",
        )
        self.assertContains(
            response,
            '<option value="__other__">Другое</option>',
            html=True,
        )

    def test_teacher_can_save_grades_from_summary_table(self):
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse("journal:assignment_detail", args=[self.assignment.pk]),
            {
                "action": "save_journal",
                f"grade_{self.student.pk}_{self.lesson.pk}": "4",
                f"attendance_{self.student.pk}_{self.lesson.pk}": "Н",
                "change_reason": "Исправление технической ошибки",
                "change_comment": "Подтверждено ведомостью",
            },
        )

        self.assertRedirects(
            response,
            reverse("journal:assignment_detail", args=[self.assignment.pk]),
        )
        self.assertEqual(
            Grade.objects.get(student=self.student, lesson=self.lesson).value,
            4,
        )
        self.assertEqual(
            Attendance.objects.get(
                student=self.student,
                lesson=self.lesson,
            ).status,
            Attendance.Status.ABSENT,
        )

    def test_teacher_can_autosave_journal_cell(self):
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:autosave_journal_cell",
                args=[self.assignment.pk],
            ),
            {
                "student_id": self.student.pk,
                "lesson_id": self.lesson.pk,
                "field": "grade",
                "value": "5",
                "original_exists": "false",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["saved"])
        self.assertEqual(response.json()["average"], 5.0)
        self.assertEqual(
            Grade.objects.get(student=self.student, lesson=self.lesson).value,
            5,
        )
        self.assertEqual(
            JournalChangeLog.objects.get().reason,
            "Первичное внесение оценки",
        )

    def test_existing_grade_requires_reason_before_autosave(self):
        Grade.objects.create(
            student=self.student,
            lesson=self.lesson,
            value=3,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:autosave_journal_cell",
                args=[self.assignment.pk],
            ),
            {
                "student_id": self.student.pk,
                "lesson_id": self.lesson.pk,
                "field": "grade",
                "value": "4",
                "original_exists": "true",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()["reason_required"])
        self.assertEqual(
            Grade.objects.get(
                student=self.student,
                lesson=self.lesson,
            ).value,
            3,
        )
        self.assertFalse(JournalChangeLog.objects.exists())

    def test_custom_change_reason_is_written_to_audit_log(self):
        Grade.objects.create(
            student=self.student,
            lesson=self.lesson,
            value=3,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse("journal:assignment_detail", args=[self.assignment.pk]),
            {
                "action": "save_journal",
                f"grade_{self.student.pk}_{self.lesson.pk}": "4",
                f"attendance_{self.student.pk}_{self.lesson.pk}": "",
                "change_reason": "__other__",
                "change_reason_other": "Исправление по решению комиссии",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            JournalChangeLog.objects.get(
                entity_type=JournalChangeLog.EntityType.GRADE,
            ).reason,
            "Исправление по решению комиссии",
        )

    def test_default_presence_does_not_create_attendance_or_audit_log(self):
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:autosave_journal_cell",
                args=[self.assignment.pk],
            ),
            {
                "student_id": self.student.pk,
                "lesson_id": self.lesson.pk,
                "field": "attendance",
                "value": "",
                "original_exists": "false",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Attendance.objects.exists())
        self.assertFalse(JournalChangeLog.objects.exists())

    def test_first_attendance_mark_does_not_require_change_reason(self):
        Attendance.objects.create(
            student=self.student,
            lesson=self.lesson,
            status=Attendance.Status.PRESENT,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:autosave_journal_cell",
                args=[self.assignment.pk],
            ),
            {
                "student_id": self.student.pk,
                "lesson_id": self.lesson.pk,
                "field": "attendance",
                "value": "Н",
                "original_exists": "true",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Attendance.objects.get(
                student=self.student,
                lesson=self.lesson,
            ).status,
            Attendance.Status.ABSENT,
        )
        self.assertEqual(
            JournalChangeLog.objects.get().reason,
            "Первичное внесение посещаемости",
        )

    def test_archived_year_rejects_teacher_autosave(self):
        AcademicYearArchive.objects.create(
            academic_year=self.assignment.academic_year,
            is_locked=True,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:autosave_journal_cell",
                args=[self.assignment.pk],
            ),
            {
                "student_id": self.student.pk,
                "lesson_id": self.lesson.pk,
                "field": "grade",
                "value": "5",
                "original_exists": "false",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Grade.objects.exists())

    def test_teacher_can_create_duplicate_lessons(self):
        self.client.login(username="teacher", password="test-password")
        lesson_data = {
            "action": "create_lesson",
            "date": "2026-06-08",
            "topic": "Введение в pandas",
        }
        url = reverse(
            "journal:assignment_detail",
            args=[self.assignment.pk],
        )

        first_response = self.client.post(url, lesson_data)
        second_response = self.client.post(url, lesson_data)

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(
            Lesson.objects.filter(
                assignment=self.assignment,
                date="2026-06-08",
                topic="Введение в pandas",
            ).count(),
            2,
        )

    def test_lesson_creation_is_written_to_operational_log(self):
        self.client.login(username="teacher", password="test-password")

        with self.assertLogs("journal.views", level="INFO") as captured:
            response = self.client.post(
                reverse(
                    "journal:assignment_detail",
                    args=[self.assignment.pk],
                ),
                {
                    "action": "create_lesson",
                    "date": "2026-06-08",
                    "topic": "Журналируемое занятие",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            any(
                "lesson_created" in message
                and f"assignment_id={self.assignment.pk}" in message
                and f"user_id={self.teacher.pk}" in message
                for message in captured.output
            )
        )

    def test_new_lesson_returns_to_assignment_edit_mode(self):
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:assignment_detail",
                args=[self.assignment.pk],
            ),
            {
                "action": "create_lesson",
                "return_to_edit": "1",
                "date": "2026-06-09",
                "topic": "Практическая работа",
            },
        )

        self.assertRedirects(
            response,
            (
                reverse(
                    "journal:assignment_detail",
                    args=[self.assignment.pk],
                )
                + "?edit=1"
            ),
        )

    def test_curriculum_import_preview_and_confirm(self):
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(
            [
                "№ п/п",
                "Дата проведения",
                "Тема и содержание занятия",
                "Вид занятия",
                "Кол-во часов",
                "Литература по теме занятия",
            ]
        )
        sheet.append([1, None, "Основы SQL", "Лекция", 1, "Л1"])
        sheet.append([2, None, "Итоговый зачёт", "Зачёт", 2, ""])
        content = BytesIO()
        workbook.save(content)
        content.seek(0)
        url = reverse(
            "journal:import_curriculum",
            args=[self.assignment.pk],
        )
        self.client.login(username="teacher", password="test-password")

        preview_response = self.client.post(
            url,
            {
                "curriculum_file": SimpleUploadedFile(
                    "ktp.xlsx",
                    content.read(),
                    content_type=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                )
            },
        )
        confirm_response = self.client.post(url, {"action": "confirm"})

        self.assertContains(preview_response, "Предварительный просмотр")
        self.assertContains(preview_response, "Основы SQL")
        self.assertRedirects(
            confirm_response,
            reverse(
                "journal:assignment_detail",
                args=[self.assignment.pk],
            ),
        )
        self.assertEqual(
            CurriculumPlanItem.objects.filter(
                assignment=self.assignment
            ).count(),
            2,
        )
        self.assertEqual(
            CurriculumPlanItem.objects.get(sequence=2).lesson_type,
            LessonType.CREDIT,
        )

    def test_pass_fail_lesson_autosaves_result(self):
        credit_lesson = Lesson.objects.create(
            assignment=self.assignment,
            date=date.today(),
            topic="Зачёт",
            lesson_type=LessonType.CREDIT,
            grading_scheme=GradingScheme.PASS_FAIL,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:autosave_journal_cell",
                args=[self.assignment.pk],
            ),
            {
                "student_id": self.student.pk,
                "lesson_id": credit_lesson.pk,
                "field": "grade",
                "value": "З",
                "reason": "Проведение зачёта",
            },
        )

        result = Grade.objects.get(
            student=self.student,
            lesson=credit_lesson,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(result.value)
        self.assertEqual(result.pass_result, Grade.PassResult.PASSED)

    def test_assignment_shows_import_or_open_curriculum_button(self):
        self.client.login(username="teacher", password="test-password")
        assignment_url = reverse(
            "journal:assignment_detail",
            args=[self.assignment.pk],
        )

        empty_response = self.client.get(assignment_url)
        CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=1,
            topic="Первая тема",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        imported_response = self.client.get(assignment_url)

        self.assertContains(empty_response, "Импортировать КТП")
        self.assertNotContains(empty_response, "Открыть КТП")
        self.assertContains(imported_response, "Открыть КТП")

    def test_teacher_can_edit_curriculum_plan(self):
        item = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=1,
            topic="Старая тема",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:curriculum_plan",
                args=[self.assignment.pk],
            ),
            {
                "action": "save",
                f"sequence_{item.pk}": "2",
                f"planned_date_{item.pk}": "2026-09-01",
                f"topic_{item.pk}": "Новая тема",
                f"lesson_type_{item.pk}": LessonType.PRACTICE,
                f"hours_{item.pk}": "2",
                f"literature_{item.pk}": "Л1",
            },
        )

        item.refresh_from_db()
        self.assertRedirects(
            response,
            reverse(
                "journal:curriculum_plan",
                args=[self.assignment.pk],
            ),
        )
        self.assertEqual(item.sequence, 1)
        self.assertEqual(item.topic, "Новая тема")
        self.assertEqual(item.lesson_type, LessonType.PRACTICE)

    def test_teacher_can_insert_curriculum_row_and_shift_following_rows(self):
        first = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=1,
            topic="Первая тема",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        second = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=2,
            topic="Вторая тема",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:curriculum_plan",
                args=[self.assignment.pk],
            ),
            {
                "action": "add",
                "insert_sequence": "2",
            },
        )

        first.refresh_from_db()
        second.refresh_from_db()
        inserted = CurriculumPlanItem.objects.get(
            assignment=self.assignment,
            sequence=2,
        )
        self.assertRedirects(
            response,
            reverse(
                "journal:curriculum_plan",
                args=[self.assignment.pk],
            ),
        )
        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 3)
        self.assertEqual(inserted.topic, "Новая тема")

    def test_duplicate_submitted_number_moves_row_and_renumbers_plan(self):
        first = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=1,
            topic="Первая",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        second = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=2,
            topic="Вторая",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        third = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=3,
            topic="Третья",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:curriculum_plan",
                args=[self.assignment.pk],
            ),
            {
                "action": "save",
                f"sequence_{first.pk}": "1",
                f"topic_{first.pk}": first.topic,
                f"lesson_type_{first.pk}": first.lesson_type,
                f"hours_{first.pk}": "1",
                f"planned_date_{first.pk}": "",
                f"literature_{first.pk}": "",
                f"sequence_{second.pk}": "2",
                f"topic_{second.pk}": second.topic,
                f"lesson_type_{second.pk}": second.lesson_type,
                f"hours_{second.pk}": "1",
                f"planned_date_{second.pk}": "",
                f"literature_{second.pk}": "",
                f"sequence_{third.pk}": "2",
                f"topic_{third.pk}": third.topic,
                f"lesson_type_{third.pk}": third.lesson_type,
                f"hours_{third.pk}": "1",
                f"planned_date_{third.pk}": "",
                f"literature_{third.pk}": "",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "journal:curriculum_plan",
                args=[self.assignment.pk],
            ),
        )
        self.assertEqual(
            list(
                CurriculumPlanItem.objects.filter(
                    assignment=self.assignment
                ).values_list("sequence", flat=True)
            ),
            [1, 2, 3],
        )

    def test_conducted_curriculum_item_cannot_be_deleted(self):
        item = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=1,
            topic="Проведённая тема",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        self.lesson.curriculum_item = item
        self.lesson.save(update_fields=["curriculum_item"])
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:delete_curriculum_item",
                args=[self.assignment.pk, item.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "journal:curriculum_plan",
                args=[self.assignment.pk],
            ),
        )
        self.assertTrue(
            CurriculumPlanItem.objects.filter(pk=item.pk).exists()
        )

    def test_deleting_curriculum_item_renumbers_following_rows(self):
        first = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=1,
            topic="Первая",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        second = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=2,
            topic="Вторая",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        third = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=3,
            topic="Третья",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:delete_curriculum_item",
                args=[self.assignment.pk, second.pk],
            )
        )

        first.refresh_from_db()
        third.refresh_from_db()
        self.assertRedirects(
            response,
            reverse(
                "journal:curriculum_plan",
                args=[self.assignment.pk],
            ),
        )
        self.assertEqual(first.sequence, 1)
        self.assertEqual(third.sequence, 2)

    def test_curriculum_shows_actual_lesson_date(self):
        item = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=1,
            topic="Проведённая тема",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        self.lesson.curriculum_item = item
        self.lesson.date = date(2026, 6, 15)
        self.lesson.save(update_fields=["curriculum_item", "date"])
        self.client.login(username="teacher", password="test-password")

        response = self.client.get(
            reverse(
                "journal:curriculum_plan",
                args=[self.assignment.pk],
            )
        )

        self.assertContains(response, "Фактическая дата")
        self.assertContains(response, "15.06.2026")

    def test_teacher_can_delete_lesson_and_keep_curriculum_item(self):
        item = CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=1,
            topic="Удаляемое занятие",
            lesson_type=LessonType.LECTURE,
            hours=1,
        )
        self.lesson.curriculum_item = item
        self.lesson.save(update_fields=["curriculum_item"])
        Grade.objects.create(
            student=self.student,
            lesson=self.lesson,
            value=5,
        )
        Attendance.objects.create(
            student=self.student,
            lesson=self.lesson,
            status=Attendance.Status.PRESENT,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse("journal:delete_lesson", args=[self.lesson.pk]),
            {"change_reason": "Занятие создано ошибочно"},
        )

        self.assertRedirects(
            response,
            reverse(
                "journal:assignment_detail",
                args=[self.assignment.pk],
            ),
        )
        self.assertFalse(Lesson.objects.filter(pk=self.lesson.pk).exists())
        self.assertTrue(
            CurriculumPlanItem.objects.filter(pk=item.pk).exists()
        )
        self.assertFalse(Grade.objects.filter(lesson_id=self.lesson.pk).exists())
        self.assertFalse(
            Attendance.objects.filter(lesson_id=self.lesson.pk).exists()
        )

    def test_other_teacher_cannot_delete_lesson(self):
        self.client.login(username="other", password="test-password")

        response = self.client.post(
            reverse("journal:delete_lesson", args=[self.lesson.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Lesson.objects.filter(pk=self.lesson.pk).exists())

    def test_grade_change_is_written_to_audit_log(self):
        Grade.objects.create(
            student=self.student,
            lesson=self.lesson,
            value=3,
        )
        self.client.login(username="teacher", password="test-password")

        response = self.client.post(
            reverse(
                "journal:autosave_journal_cell",
                args=[self.assignment.pk],
            ),
            {
                "student_id": self.student.pk,
                "lesson_id": self.lesson.pk,
                "field": "grade",
                "value": "4",
                "reason": "Исправление технической ошибки",
                "comment": "Подтверждено ведомостью текущего контроля",
            },
        )

        log = JournalChangeLog.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(log.old_value, "3")
        self.assertEqual(log.new_value, "4")
        self.assertEqual(
            log.reason,
            "Исправление технической ошибки",
        )


class AssignmentAdminTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )
        self.teacher = user_model.objects.create_user(
            username="teacher",
            password="test-password",
        )
        self.group = StudyGroup.objects.create(
            name="ИС-31",
            admission_year=2023,
        )
        self.student = Student.objects.create(
            group=self.group,
            last_name="Сидоров",
            first_name="Павел",
            middle_name="Ильич",
            student_card_number="2023-101",
        )
        self.subject = Subject.objects.create(name="Базы данных")
        self.assignment = TeachingAssignment.objects.create(
            teacher=self.teacher,
            group=self.group,
            subject=self.subject,
            academic_year="2025/2026",
            semester=TeachingAssignment.Semester.SECOND,
        )
        self.client.login(username="admin", password="test-password")

    def test_subject_page_has_assignment_button_and_read_only_table(self):
        response = self.client.get(
            reverse("admin:journal_subject_change", args=[self.subject.pk])
        )

        self.assertContains(response, "Назначить дисциплину")
        self.assertContains(response, "История")
        self.assertContains(response, "Удалить")
        self.assertContains(response, "ИС-31")
        self.assertNotContains(response, "Добавить еще один Назначение")
        self.assertContains(response, 'value="Сохранить"')
        self.assertContains(response, 'value="Сохранить и выйти"')
        self.assertNotContains(response, "Сохранить и добавить другой объект")
        self.assertNotContains(
            response,
            "Сохранить и продолжить редактирование",
        )

    def test_admin_can_manage_single_college_information_record(self):
        add_url = reverse("admin:journal_collegeinformation_add")
        response = self.client.post(
            add_url,
            {
                "name": "ГБПОУ Примерный колледж",
                "address": "г. Москва, ул. Учебная, д. 1",
                "inn": "7701234567",
                "email": "college@example.ru",
                "_continue": "Сохранить",
            },
        )

        self.assertEqual(CollegeInformation.objects.count(), 1)
        college = CollegeInformation.objects.get()
        self.assertEqual(college.name, "ГБПОУ Примерный колледж")
        self.assertRedirects(
            response,
            reverse(
                "admin:journal_collegeinformation_change",
                args=[college.pk],
            ),
        )
        self.assertEqual(self.client.get(add_url).status_code, 403)

    def test_group_page_has_read_only_student_table(self):
        response = self.client.get(
            reverse("admin:journal_studygroup_change", args=[self.group.pk])
        )

        self.assertContains(response, "Студенты группы")
        self.assertContains(response, "Сидоров")
        self.assertContains(response, "2023-101")
        self.assertNotContains(response, "Добавить еще один Студент")
        self.assertNotContains(
            response,
            reverse("admin:journal_student_change", args=[self.student.pk]),
        )

    def test_admin_can_import_and_update_students_from_xlsx(self):
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(
            [
                "Фамилия",
                "Имя",
                "Отчество",
                "Номер студенческого билета",
                "Обучается",
            ]
        )
        sheet.append(
            [
                "Иванова",
                "Анна",
                "Сергеевна",
                "2026-001",
                "Да",
            ]
        )
        sheet.append(
            [
                "Сидоров",
                "Павел",
                "Ильич",
                "2023-101",
                "Нет",
            ]
        )
        content = BytesIO()
        workbook.save(content)
        content.seek(0)

        response = self.client.post(
            reverse("admin:journal_student_import"),
            {
                "group": self.group.pk,
                "student_file": SimpleUploadedFile(
                    "students.xlsx",
                    content.read(),
                    content_type=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                ),
            },
        )

        self.assertRedirects(
            response,
            reverse("admin:journal_student_changelist"),
        )
        student = Student.objects.get(
            student_card_number="2026-001"
        )
        self.assertEqual(student.group, self.group)
        self.assertEqual(student.last_name, "Иванова")
        self.assertTrue(student.is_active)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

    def test_student_list_has_xlsx_import_button(self):
        response = self.client.get(
            reverse("admin:journal_student_changelist")
        )

        self.assertContains(response, "Импортировать из XLSX")
        self.assertContains(
            response,
            reverse("admin:journal_student_import"),
        )

    def test_assignment_add_page_prefills_subject(self):
        AcademicYearArchive.objects.create(
            academic_year="2026/2027",
        )
        response = self.client.get(
            reverse("admin:journal_teachingassignment_add"),
            {"subject": self.subject.pk},
        )

        self.assertContains(
            response,
            f'<option value="{self.subject.pk}" selected>',
            html=False,
        )
        self.assertContains(
            response,
            '<option value="2026/2027">2026/2027</option>',
            html=False,
        )
        self.assertContains(
            response,
            '<select name="academic_year"',
            html=False,
        )

    def test_locked_academic_year_is_not_available_for_new_assignment(self):
        AcademicYearArchive.objects.create(
            academic_year="2027/2028",
            is_locked=True,
        )

        response = self.client.get(
            reverse("admin:journal_teachingassignment_add")
        )

        self.assertNotContains(
            response,
            '<option value="2027/2028">',
            html=False,
        )

    def test_admin_index_shows_welcome_and_system_summary(self):
        CollegeInformation.objects.create(
            name="ГБПОУ Примерный колледж",
        )
        response = self.client.get(reverse("admin:index"))

        self.assertContains(response, "ГБПОУ Примерный колледж")
        self.assertContains(response, "Добро пожаловать, admin!")
        self.assertContains(response, "Состояние электронного журнала")
        self.assertContains(response, "Студентов")
        self.assertContains(response, "Учебных групп")
        self.assertContains(response, "Назначений дисциплин")
        self.assertContains(response, "Проведённых занятий")
        self.assertContains(response, "Версия системы: 1.2.0")

    def test_eighth_semester_is_available_and_exported(self):
        self.assignment.semester = TeachingAssignment.Semester.EIGHTH
        self.assignment.save(update_fields=["semester"])
        Lesson.objects.create(
            assignment=self.assignment,
            date=date.today(),
            topic="Итоговое занятие",
        )

        response = self.client.get(
            reverse(
                "admin:journal_teachingassignment_change",
                args=[self.assignment.pk],
            )
        )
        csv_content = _build_csv(self.assignment).decode("utf-8-sig")

        self.assertContains(response, "8 семестр")
        self.assertIn("8 семестр", csv_content)

    def test_quick_delete_removes_assignment(self):
        response = self.client.post(
            reverse(
                "admin:journal_teachingassignment_quick_delete",
                args=[self.assignment.pk],
            ),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            TeachingAssignment.objects.filter(pk=self.assignment.pk).exists()
        )

    def test_lesson_list_has_separate_assignment_columns(self):
        Lesson.objects.create(
            assignment=self.assignment,
            date=date.today(),
            topic="Проектирование таблиц",
        )

        response = self.client.get(reverse("admin:journal_lesson_changelist"))

        expected_headers = [
            "Дата занятия",
            "Дисциплина",
            "Тема занятия",
            "Преподаватель",
            "Группа",
            "Учебный год",
            "Семестр",
        ]
        for header in expected_headers:
            self.assertContains(response, header)

        self.assertContains(response, "Базы данных")
        self.assertContains(response, "Проектирование таблиц")
        self.assertContains(response, "ИС-31")
        self.assertContains(response, "2025/2026")

    def test_curriculum_list_has_subject_and_teacher_filters(self):
        self.teacher.first_name = "Иван"
        self.teacher.last_name = "Иванов"
        self.teacher.save(update_fields=["first_name", "last_name"])
        UserProfile.objects.create(
            user=self.teacher,
            middle_name="Иванович",
        )
        CurriculumPlanItem.objects.create(
            assignment=self.assignment,
            sequence=1,
            topic="Основы реляционных баз данных",
        )
        response = self.client.get(
            reverse("admin:journal_curriculumplanitem_changelist")
        )

        self.assertContains(response, "Дисциплина")
        self.assertContains(response, "Преподаватель")
        self.assertContains(response, "Иванов Иван Иванович")

    def test_user_form_has_middle_name_and_teacher_choices_use_full_name(self):
        self.teacher.first_name = "Иван"
        self.teacher.last_name = "Иванов"
        self.teacher.save(update_fields=["first_name", "last_name"])
        UserProfile.objects.create(
            user=self.teacher,
            middle_name="Иванович",
        )

        user_response = self.client.get(
            reverse("admin:auth_user_change", args=[self.teacher.pk])
        )
        assignment_response = self.client.get(
            reverse(
                "admin:journal_teachingassignment_change",
                args=[self.assignment.pk],
            )
        )

        self.assertContains(user_response, "Отчество")
        user_content = user_response.content.decode()
        personal_info_position = user_content.index("Персональная информация")
        middle_name_position = user_content.index("Отчество")
        permissions_position = user_content.index("Права доступа")
        self.assertLess(personal_info_position, middle_name_position)
        self.assertLess(middle_name_position, permissions_position)
        self.assertContains(
            assignment_response,
            "Иванов Иван Иванович",
        )
        self.assertEqual(
            user_full_name(self.teacher),
            "Иванов Иван Иванович",
        )

    def test_admin_can_download_three_file_report_package(self):
        Lesson.objects.create(
            assignment=self.assignment,
            date=date.today(),
            topic="Отчётное занятие",
        )

        response = self.client.post(
            reverse("admin:journal_teachingassignment_changelist"),
            {
                "action": "download_report_package",
                "_selected_action": [self.assignment.pk],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            names = archive.namelist()
        self.assertEqual(len(names), 3)
        self.assertTrue(any(name.endswith(".pdf") for name in names))
        self.assertTrue(any(name.endswith(".csv") for name in names))
        self.assertTrue(any(name.endswith("_changes.xlsx") for name in names))

    def test_pdf_metrics_use_all_lessons_not_current_page(self):
        lessons = [
            Lesson.objects.create(
                assignment=self.assignment,
                date=date.today(),
                topic=f"Занятие {number}",
            )
            for number in range(1, 12)
        ]
        first_grade = Grade.objects.create(
            student=self.student,
            lesson=lessons[0],
            value=3,
        )
        second_grade = Grade.objects.create(
            student=self.student,
            lesson=lessons[10],
            value=5,
        )
        first_absence = Attendance.objects.create(
            student=self.student,
            lesson=lessons[1],
            status=Attendance.Status.ABSENT,
        )
        second_absence = Attendance.objects.create(
            student=self.student,
            lesson=lessons[10],
            status=Attendance.Status.EXCUSED,
        )

        metrics = _student_summary_metrics(
            [self.student],
            lessons,
            {
                (self.student.id, first_grade.lesson_id): first_grade,
                (self.student.id, second_grade.lesson_id): second_grade,
            },
            {
                (self.student.id, first_absence.lesson_id): first_absence,
                (self.student.id, second_absence.lesson_id): second_absence,
            },
        )

        self.assertEqual(metrics[self.student.id]["average"], "4,00")
        self.assertEqual(metrics[self.student.id]["absence_count"], 2)

    def test_admin_can_close_download_and_reopen_academic_year(self):
        CollegeInformation.objects.create(
            name="ГБПОУ Примерный колледж",
        )
        Lesson.objects.create(
            assignment=self.assignment,
            date=date.today(),
            topic="Архивное занятие",
        )
        archive_record = AcademicYearArchive.objects.create(
            academic_year=self.assignment.academic_year,
            order_number="15-од",
            order_date=date.today(),
        )
        changelist_url = reverse(
            "admin:journal_academicyeararchive_changelist"
        )

        close_response = self.client.post(
            changelist_url,
            {
                "action": "close_academic_year",
                "_selected_action": [archive_record.pk],
            },
        )

        self.assertEqual(close_response.status_code, 302)
        archive_record.refresh_from_db()
        self.assertTrue(archive_record.is_locked)
        self.assertTrue(archive_record.archive_data)
        self.assertEqual(len(archive_record.checksum), 64)
        self.assertEqual(
            AcademicYearArchiveEvent.objects.filter(
                archive=archive_record,
                action=AcademicYearArchiveEvent.Action.CLOSE,
            ).count(),
            1,
        )
        with zipfile.ZipFile(BytesIO(bytes(archive_record.archive_data))) as archive:
            self.assertIn("registry.csv", archive.namelist())

        download_response = self.client.post(
            changelist_url,
            {
                "action": "download_academic_year_archive",
                "_selected_action": [archive_record.pk],
            },
        )
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(
            download_response["Content-Type"],
            "application/zip",
        )

        archive_record.reopen_reason = "Исправление итоговой ведомости"
        archive_record.save(update_fields=["reopen_reason"])
        reopen_response = self.client.post(
            changelist_url,
            {
                "action": "reopen_academic_year",
                "_selected_action": [archive_record.pk],
            },
        )
        self.assertEqual(reopen_response.status_code, 302)
        archive_record.refresh_from_db()
        self.assertFalse(archive_record.is_locked)
        self.assertEqual(
            archive_record.reopen_reason,
            "Исправление итоговой ведомости",
        )
        self.assertEqual(archive_record.reopened_by, self.admin)
        self.assertEqual(
            AcademicYearArchiveEvent.objects.filter(
                archive=archive_record,
                action=AcademicYearArchiveEvent.Action.REOPEN,
            ).count(),
            1,
        )
