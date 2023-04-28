from django.test import TestCase
from neomodel import config, db, clear_neo4j_database

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

# to use the default database "neo4j" for tests
# because test database for neomodel isn't supported by django?
config.DATABASE_URL = os.environ['NEO4J_BOLT_URL']
# clear_neo4j_database() doesn't delete constraints

class IndexViewTestCase(TestCase):
    def setUp(self):
        clear_neo4j_database(db)
        person1 = Person(title="Prof", name="Adviso").save()
        person2 = Person(name="Person").save()
        interest = ResearchInterest(name="interest").save()
        institute = Institute(name="institute").save()
        fac = Faculty(name="faculty").save()
        dep = Department(name="department").save()
        role = Role(name="role").save()
        offered_exp = Expertise(name="offered E").save()
        wanted_exp = Expertise(name="wanted E").save()

    def test_suggestions_count(self):
        response = self.client.get("/expertise/")
        suggestions = response.context["suggestions"]

        self.assertEqual(2, len(suggestions["persons"]["options"]))
        self.assertEqual(1, len(suggestions["interests"]["options"]))
        self.assertEqual(1, len(suggestions["institutes"]["options"]))
        self.assertEqual(1, len(suggestions["faculties"]["options"]))
        self.assertEqual(1, len(suggestions["departments"]["options"]))
        self.assertEqual(2, len(suggestions["advisors"]["options"]))
        self.assertEqual(1, len(suggestions["roles"]["options"]))
        self.assertEqual(2, len(suggestions["offered_expertise"]["options"]))
        self.assertEqual(2, len(suggestions["wanted_expertise"]["options"]))

    def test_suggestions_format(self):
        response = self.client.get("/expertise/")
        suggestions = response.context["suggestions"]

        for key in suggestions:
            self.assertIn("group", suggestions[key])
            self.assertIn("options", suggestions[key])

    def test_used_template(self):
        response = self.client.get("/expertise/")
        templates = response.templates

        self.assertEqual("expertise/index.html", templates[0].name)
        self.assertEqual("expertise/base.html", templates[1].name)

