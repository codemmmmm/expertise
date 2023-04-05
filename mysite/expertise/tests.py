from dataclasses import dataclass

from django.test import TestCase

from expertise.models import (
    Person,
    ResearchInterest,
    Institute,
    Faculty,
    Department,
    Role,
    Expertise
)
from .views import *

@dataclass
class PersonData:
    def __init__(self, title, name, email, pk):
        self.title = title
        self.name = name
        self.email = email
        self.pk = pk

class PersonsViewTestCase(TestCase):
    def setUp(self):
        pass

    def test_person_matched1(self):
        person = PersonData("Prof", "Nagel", "", "as155")
        self.assertTrue(person_contains_value(person, "nage"))
