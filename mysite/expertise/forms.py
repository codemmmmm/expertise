from django import forms

from expertise.models import (
    Person,
    ResearchInterest,
    Institute,
    Faculty,
    Department,
    Role,
    Expertise
)

class MultipleChoiceAndNewField(forms.MultipleChoiceField):
    """MultipleChoiceField but new values are allowed"""
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

    )
    email = forms.EmailField(
        label="Email address",
        required=True,
        max_length=50,
        help_text="Please enter your institute email.",
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
    person_choices = get_choices(Person)
    interest_choices = get_choices(ResearchInterest)
    institute_choices = get_choices(Institute)
    faculty_choices = get_choices(Faculty)
    department_choices = get_choices(Department)
    role_choices = get_choices(Role)
    expertise_choices = get_choices(Expertise)

    widget = forms.SelectMultiple(attrs={"class": "form-select"})
    interests = MultipleChoiceAndNewField(choices=interest_choices, label="Research interests", required=False, widget=widget)
    institutes = MultipleChoiceAndNewField(choices=institute_choices, label="Institute", required=False, widget=widget)
    faculties = MultipleChoiceAndNewField(choices=faculty_choices, label="Faculty", required=False, widget=widget)
    departments = MultipleChoiceAndNewField(choices=department_choices, label="Department", required=False, widget=widget)
    advisors = MultipleChoiceAndNewField(choices=person_choices, label="Advisor", required=False, widget=widget)
    roles = MultipleChoiceAndNewField(choices=role_choices, label="Role in ScaDS.AI", required=False, widget=widget)
    offered = MultipleChoiceAndNewField(choices=expertise_choices, label="Offered expertise", required=False, widget=widget)
    wanted = MultipleChoiceAndNewField(choices=expertise_choices, label="Wanted expertise", required=False, widget=widget)