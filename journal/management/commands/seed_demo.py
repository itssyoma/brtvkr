from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from journal.models import (
    Attendance,
    Grade,
    Lesson,
    Student,
    StudyGroup,
    Subject,
    TeachingAssignment,
)


class Command(BaseCommand):
    help = "Создаёт демонстрационные данные электронного журнала"

    def handle(self, *args, **options):
        user_model = get_user_model()
        admin, _ = user_model.objects.get_or_create(
            username="admin",
            defaults={
                "first_name": "Администратор",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("admin12345")
        admin.save()

        teacher, _ = user_model.objects.get_or_create(
            username="teacher",
            defaults={
                "first_name": "Ирина",
                "last_name": "Петрова",
                "is_staff": True,
            },
        )
        teacher.is_staff = True
        teacher.set_password("teacher12345")
        teacher.save()

        group, _ = StudyGroup.objects.get_or_create(
            name="ИСП-21",
            defaults={"admission_year": 2024, "curator": teacher},
        )
        subject, _ = Subject.objects.get_or_create(
            name="Основы программирования",
            defaults={"short_name": "ОП"},
        )
        assignment = TeachingAssignment.objects.filter(
            teacher=teacher,
            group=group,
            subject=subject,
        ).first()
        if assignment is None:
            assignment = TeachingAssignment.objects.create(
                teacher=teacher,
                group=group,
                subject=subject,
                academic_year="2025/2026",
                semester=TeachingAssignment.Semester.SECOND,
            )
        else:
            assignment.academic_year = "2025/2026"
            assignment.semester = TeachingAssignment.Semester.SECOND
            assignment.save(
                update_fields=["academic_year", "semester"],
            )

        names = [
            ("Иванов", "Алексей", "Сергеевич", "2024-001"),
            ("Смирнова", "Анна", "Олеговна", "2024-002"),
            ("Кузнецов", "Максим", "Игоревич", "2024-003"),
            ("Соколова", "Мария", "Андреевна", "2024-004"),
            ("Попов", "Дмитрий", "Романович", "2024-005"),
        ]
        students = []
        for last_name, first_name, middle_name, card_number in names:
            student, _ = Student.objects.get_or_create(
                student_card_number=card_number,
                defaults={
                    "group": group,
                    "last_name": last_name,
                    "first_name": first_name,
                    "middle_name": middle_name,
                },
            )
            students.append(student)

        lesson, _ = Lesson.objects.get_or_create(
            assignment=assignment,
            date=date.today(),
            topic="Введение в язык Python",
        )
        demo_grades = [5, 4, 5, 3, 4]
        demo_statuses = [
            Attendance.Status.PRESENT,
            Attendance.Status.PRESENT,
            Attendance.Status.LATE,
            Attendance.Status.EXCUSED,
            Attendance.Status.PRESENT,
        ]
        for student, grade, status in zip(
            students,
            demo_grades,
            demo_statuses,
            strict=True,
        ):
            Grade.objects.update_or_create(
                student=student,
                lesson=lesson,
                defaults={"value": grade},
            )
            Attendance.objects.update_or_create(
                student=student,
                lesson=lesson,
                defaults={"status": status},
            )

        self.stdout.write(self.style.SUCCESS("Демонстрационные данные созданы."))
        self.stdout.write("Администратор: admin / admin12345")
        self.stdout.write("Преподаватель: teacher / teacher12345")
