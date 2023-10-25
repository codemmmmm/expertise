from django import forms
from django.core.exceptions import ValidationError

from expertise.models import (
    Person,
    ResearchInterest,
    Institute,
    Faculty,
    Department,
    Role,
    Expertise
)

# TODO: validate should also validate each list item's length
class MultipleChoiceAndNewField(forms.MultipleChoiceField):
    """MultipleChoiceField but new values are allowed"""
    def to_python(self, value):
        if not value:
            return []
        elif not isinstance(value, (list, tuple)):
            raise ValidationError(
                self.error_messages["invalid_list"], code="invalid_list"
            )
        # remove duplicates with set
        return list({str(val) for val in value})

    def validate(self, value):
        """Validate that the input is a list or tuple."""
        if self.required and not value:
            raise ValidationError(self.error_messages["required"], code="required")

def get_choices(model_class):
    return [(x.pk, x.name) for x in model_class.nodes.all()]

class EditForm(forms.Form):
    """edit form excluding the person"""
    # if a helptext is added to a field, the widget also needs aria-describedby
    name = forms.CharField(
        label="First and last name",
        required=True,
        max_length=80,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Email address",
        required=True,
        max_length=50,
        help_text="Please enter your institution email.",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "aria-describedby": "id_email_helptext"})
    )
    title = forms.CharField(
        label="Academic title",
        required=False,
        max_length=40,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    interests = MultipleChoiceAndNewField(
        label="Topics of interest",
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select interest"})
    )
    institutes = MultipleChoiceAndNewField(
        label="Institution",
        required=False,
        help_text="Universities, research institutions, ...",
        widget=forms.SelectMultiple(attrs={"class": "form-select institute"})
    )
    faculties = MultipleChoiceAndNewField(
        label="Faculty, center",
        required=False,
        help_text="University institutes, university faculties, centers, ...",
        widget=forms.SelectMultiple(attrs={"class": "form-select faculty"})
    )
    departments = MultipleChoiceAndNewField(
        label="Department, group",
        required=False,
        help_text="Departments, groups, chairs, ...",
        widget=forms.SelectMultiple(attrs={"class": "form-select department"})
    )
    advisors = MultipleChoiceAndNewField(
        label="Advisor",
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select person"})
    )
    roles = MultipleChoiceAndNewField(
        label="Role in ScaDS.AI",
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select role"})
    )
    offered = MultipleChoiceAndNewField(
        label="Offered expertise",
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select expertise"})
    )
    wanted = MultipleChoiceAndNewField(
        label="Wanted expertise",
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select expertise"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # otherwise the form field choices are not updated after the first initialization
        person_choices = get_choices(Person)
        interest_choices = get_choices(ResearchInterest)
        institute_choices = get_choices(Institute)
        faculty_choices = get_choices(Faculty)
        department_choices = get_choices(Department)
        role_choices = get_choices(Role)
        expertise_choices = get_choices(Expertise)

        self.fields["interests"].choices = interest_choices
        self.fields["institutes"].choices = institute_choices
        self.fields["faculties"].choices = faculty_choices
        self.fields["departments"].choices = department_choices
        self.fields["advisors"].choices = person_choices
        self.fields["roles"].choices = role_choices
        self.fields["offered"].choices = expertise_choices
        self.fields["wanted"].choices = expertise_choices