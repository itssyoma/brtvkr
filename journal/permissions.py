ADMINISTRATORS = "Администраторы"
ACADEMIC_OFFICE = "Учебная часть"
TEACHERS = "Преподаватели"
CURATORS = "Кураторы"
AUDITORS = "Аудиторы"

STAFF_GROUPS = {
    ADMINISTRATORS,
    ACADEMIC_OFFICE,
    AUDITORS,
}

ROLE_PERMISSION_CODENAMES = {
    ACADEMIC_OFFICE: {
        "view_collegeinformation",
        "view_subject",
        "add_subject",
        "change_subject",
        "view_teachingassignment",
        "add_teachingassignment",
        "change_teachingassignment",
        "delete_teachingassignment",
        "view_curriculumplanitem",
        "view_lesson",
        "view_grade",
        "view_attendance",
        "view_journalchangelog",
        "view_student",
        "add_student",
        "change_student",
        "delete_student",
        "view_studygroup",
        "add_studygroup",
        "change_studygroup",
        "delete_studygroup",
        "view_academicyeararchive",
        "add_academicyeararchive",
        "change_academicyeararchive",
        "view_academicyeararchiveevent",
    },
    TEACHERS: {
        "view_subject",
        "view_teachingassignment",
        "view_curriculumplanitem",
        "view_lesson",
        "view_grade",
        "view_attendance",
    },
    CURATORS: {
        "view_subject",
        "view_teachingassignment",
        "view_lesson",
        "view_grade",
        "view_attendance",
        "view_student",
        "view_studygroup",
    },
    AUDITORS: {
        "view_collegeinformation",
        "view_subject",
        "view_teachingassignment",
        "view_curriculumplanitem",
        "view_lesson",
        "view_grade",
        "view_attendance",
        "view_journalchangelog",
        "view_student",
        "view_studygroup",
        "view_academicyeararchive",
        "view_academicyeararchiveevent",
    },
}


def user_in_group(user, group_name):
    return (
        user.is_authenticated
        and user.groups.filter(name=group_name).exists()
    )


def is_system_administrator(user):
    return user.is_superuser or user_in_group(user, ADMINISTRATORS)


def is_academic_office(user):
    return user_in_group(user, ACADEMIC_OFFICE)


def is_auditor(user):
    return user_in_group(user, AUDITORS)


def can_view_all_journals(user):
    return (
        is_system_administrator(user)
        or is_academic_office(user)
        or is_auditor(user)
    )


def can_manage_academic_structure(user):
    return is_system_administrator(user) or is_academic_office(user)


def can_download_reports(user):
    return can_view_all_journals(user)


def user_role_name(user):
    if is_system_administrator(user):
        return "администратор"
    if is_academic_office(user):
        return "учебная часть"
    if is_auditor(user):
        return "аудитор"
    if user_in_group(user, CURATORS):
        return "куратор"
    return "преподаватель"
