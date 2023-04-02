from django.db import models

from neomodel import StructuredNode, StringProperty, EmailProperty, RelationshipTo

# TODO: maybe create Model form for Edit site

class ResearchInterest(StructuredNode):
    name = StringProperty(unique_index=True, required=True)

class Institute(StructuredNode):
    name = StringProperty(unique_index=True, required=True)

class Faculty(StructuredNode):
    name = StringProperty(unique_index=True, required=True)

class Department(StructuredNode):
    name = StringProperty(unique_index=True, required=True)

class Expertise(StructuredNode):
    name = StringProperty(unique_index=True, required=True)

class Role(StructuredNode):
    name = StringProperty(unique_index=True, required=True)

class Person(StructuredNode):
    name = StringProperty(required=True)
    # not required because people mentioned as advisors might not have any data entered
    email = EmailProperty(unique_index=True)
    title = StringProperty()
    comment = StringProperty()

    interests = RelationshipTo(ResearchInterest, 'HAS')
    institutes = RelationshipTo(Institute, 'MEMBER_OF')
    faculties = RelationshipTo(Faculty, 'MEMBER_OF')
    departments = RelationshipTo(Department, 'MEMBER_OF')
    roles = RelationshipTo(Role, 'HAS')
    offered_expertise = RelationshipTo(Expertise, 'OFFERS')
    wanted_expertise = RelationshipTo(Expertise, 'WANTS')
    advisors = RelationshipTo('Person', 'ADVISED_BY')

