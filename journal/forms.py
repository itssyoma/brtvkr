from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import (
    AcademicYearArchive,
    StudyGroup,
    TeachingAssignment,
    UserProfile,
    user_full_name,
)


class FullNameUserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        return user_full_name(user)


class UserMiddleNameMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                self.fields["middle_name"].initial = (
                    self.instance.journal_profile.middle_name
                )
            except UserProfile.DoesNotExist:
                pass


class CollegeUserChangeForm(UserMiddleNameMixin, UserChangeForm):
    middle_name = forms.CharField(
        label="Отчество",
        max_length=150,
        required=False,
    )


class CollegeUserCreationForm(UserMiddleNameMixin, UserCreationForm):
    middle_name = forms.CharField(
        label="Отчество",
        max_length=150,
        required=False,
    )


class TeachingAssignmentAdminForm(forms.ModelForm):
    academic_year = forms.ChoiceField(label="Учебный год")
    teacher = FullNameUserChoiceField(
        label="Преподаватель",
        queryset=get_user_model().objects.all(),
    )

    class Meta:
        model = TeachingAssignment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        years = list(
            AcademicYearArchive.objects.filter(
                is_locked=False
            ).order_by(
                "-academic_year"
            ).values_list("academic_year", flat=True)
        )
        if (
            self.instance
            and self.instance.pk
            and self.instance.academic_year not in years
        ):
            years.append(self.instance.academic_year)
            years.sort(reverse=True)
        self.fields["academic_year"].choices = [
            (year, year) for year in years
        ]
        self.fields["academic_year"].help_text = (
            "Доступны открытые годы из раздела «Учебные годы и архив»."
        )

    def clean_academic_year(self):
        academic_year = self.cleaned_data["academic_year"]
        if not AcademicYearArchive.objects.filter(
            academic_year=academic_year
        ).exists():
            raise forms.ValidationError(
                "Выберите учебный год из справочника."
            )
        return academic_year


class StudyGroupAdminForm(forms.ModelForm):
    curator = FullNameUserChoiceField(
        label="Куратор",
        queryset=get_user_model().objects.all(),
        required=False,
    )

    class Meta:
        model = StudyGroup
        fields = "__all__"


class StudentImportForm(forms.Form):
    group = forms.ModelChoiceField(
        label="Учебная группа",
        queryset=StudyGroup.objects.all(),
    )
    student_file = forms.FileField(
        label="Файл со студентами",
        help_text="Поддерживается формат .xlsx.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )

    def clean_student_file(self):
        uploaded_file = self.cleaned_data["student_file"]
        if not uploaded_file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Выберите файл в формате XLSX.")
        return uploaded_file
