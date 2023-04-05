from neomodel import StringProperty, EmailProperty, RelationshipTo, UniqueIdProperty
from django_neomodel import DjangoNode

class ResearchInterest(DjangoNode):
    name = StringProperty(unique_index=True, required=True)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'

class Institute(DjangoNode):
    name = StringProperty(unique_index=True, required=True)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'

class Faculty(DjangoNode):
    name = StringProperty(unique_index=True, required=True)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'
        verbose_name_plural = 'faculties'

class Department(DjangoNode):
    name = StringProperty(unique_index=True, required=True)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'

class Expertise(DjangoNode):
    name = StringProperty(unique_index=True, required=True)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'
        verbose_name_plural = 'expertise'

class Role(DjangoNode):
    name = StringProperty(unique_index=True, required=True)
    # only needed to make admin site work
    pk = UniqueIdProperty()

    class Meta:
        app_label = 'expertise'

class Person(DjangoNode):
    name = StringProperty(required=True)
    # not required because people mentioned as advisors might not have any data entered
    email = EmailProperty(unique_index=True)
    title = StringProperty()
    comment = StringProperty()
    # only needed to make admin site work
    pk = UniqueIdProperty()

    interests = RelationshipTo(ResearchInterest, 'HAS')
    institutes = RelationshipTo(Institute, 'MEMBER_OF')
    faculties = RelationshipTo(Faculty, 'MEMBER_OF')
    departments = RelationshipTo(Department, 'MEMBER_OF')
    roles = RelationshipTo(Role, 'HAS')
    offered_expertise = RelationshipTo(Expertise, 'OFFERS')
    wanted_expertise = RelationshipTo(Expertise, 'WANTS')
    advisors = RelationshipTo('Person', 'ADVISED_BY')

    class Meta:
        app_label = 'expertise'
