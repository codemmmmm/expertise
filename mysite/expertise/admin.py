from django.contrib import admin as django_admin

from django_neomodel import admin as neo_admin
from expertise.models import (
    Person,
    ResearchInterest,
    Institute,
    Faculty,
    Department,
    Role,
    Expertise
)

class NoDeleteAdmin:
    def has_delete_permission(self, request, obj=None):
        # disable delete
        return False

class PersonAdmin(NoDeleteAdmin, django_admin.ModelAdmin):
    list_display = ('name', 'email')
    exclude = ('pk',)

class ResearchInterestAdmin(NoDeleteAdmin, django_admin.ModelAdmin):
    list_display = ('name',)
    exclude = ('pk',)

class InstituteAdmin(NoDeleteAdmin, django_admin.ModelAdmin):
    list_display = ('name',)
    exclude = ('pk',)

class FacultyAdmin(NoDeleteAdmin, django_admin.ModelAdmin):
    list_display = ('name',)
    exclude = ('pk',)

class DepartmentAdmin(NoDeleteAdmin, django_admin.ModelAdmin):
    list_display = ('name',)
    exclude = ('pk',)

class RoleAdmin(NoDeleteAdmin, django_admin.ModelAdmin):
    list_display = ('name',)
    exclude = ('pk',)

class ExpertiseAdmin(NoDeleteAdmin, django_admin.ModelAdmin):
    list_display = ('name',)
    exclude = ('pk',)

neo_admin.register(Person, PersonAdmin)
neo_admin.register(ResearchInterest, ResearchInterestAdmin)
neo_admin.register(Institute, InstituteAdmin)
neo_admin.register(Faculty, FacultyAdmin)
neo_admin.register(Department, DepartmentAdmin)
neo_admin.register(Role, RoleAdmin)
neo_admin.register(Expertise, ExpertiseAdmin)
