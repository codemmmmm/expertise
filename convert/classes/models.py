"""this is a copy of the model file from Django with the functions and the
django_neomodel dependency removed"""
from neomodel import StringProperty, EmailProperty, RelationshipTo, UniqueIdProperty, StructuredNode

class ResearchInterest(StructuredNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'

class Institute(StructuredNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'

class Faculty(StructuredNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'
        verbose_name_plural = 'faculties'

class Department(StructuredNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'

class Expertise(StructuredNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'
        verbose_name_plural = 'expertise'

class Role(StructuredNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'

class Person(StructuredNode):
    name = StringProperty(required=True, max_length=120)
    # not required because people mentioned as advisors might not have any data entered
    email = EmailProperty(unique_index=True)
    title = StringProperty(max_length=60)
    comment = StringProperty(max_length=500)
    pk = UniqueIdProperty()

    interests = RelationshipTo(ResearchInterest, "INTERESTED_IN")
    institutes = RelationshipTo(Institute, "MEMBER_OF")
    faculties = RelationshipTo(Faculty, "MEMBER_OF")
    departments = RelationshipTo(Department, "MEMBER_OF")
    roles = RelationshipTo(Role, "HAS")
    offered_expertise = RelationshipTo(Expertise, "OFFERS")
    wanted_expertise = RelationshipTo(Expertise, "WANTS")
    advisors = RelationshipTo("Person", "ADVISED_BY")

    class Meta:
        app_label = "expertise"
