import os
from django.test import TestCase
from neomodel import config, db, clear_neo4j_database, DoesNotExist

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
url_with_database = os.environ['NEO4J_BOLT_URL']
split_url = url_with_database.split("/")
split_url[-1] = "test"
config.DATABASE_URL = "/".join(split_url)

# should I also delete constraints with clear_neo4j_database ?

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

class PersonApiTestCase(TestCase):
    def setUp(self):
        clear_neo4j_database(db)
        person1 = Person(title="Prof", name="Adviso", comment="I am hiring").save()
        person2 = Person(name="Person").save()
        interest = ResearchInterest(name="interest").save()
        institute = Institute(name="institute").save()
        fac = Faculty(name="faculty").save()
        dep = Department(name="department").save()
        role = Role(name="role").save()
        offered_exp = Expertise(name="offered E").save()
        wanted_exp = Expertise(name="wanted E").save()

    def test_missing_parameter(self):
        response = self.client.get("/expertise/persons")
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.json())

    def test_correct_response(self):
        response = self.client.get("/expertise/persons?search=")
        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("error", json)
        self.assertIn("persons", json)
        self.assertEqual(2, len(json["persons"]))
        for entry in json["persons"]:
            self.assertIn("person", entry)
            self.assertNotIn("comment", entry["person"])
            self.assertIn("interests", entry)
            self.assertIn("institutes", entry)
            self.assertIn("faculties", entry)
            self.assertIn("departments", entry)
            self.assertIn("roles", entry)
            self.assertIn("offered", entry)
            self.assertIn("wanted", entry)
            self.assertIn("advisors", entry)

        response = self.client.get("/expertise/persons?search=thisDataDoesNotExist")
        json = response.json()
        self.assertEqual([], json["persons"])

class GraphApiTestCase(TestCase):
    def setUp(self):
        clear_neo4j_database(db)
        # nodes
        person1 = Person(title="Prof", name="Adviso", comment="I am hiring").save()
        person2 = Person(name="Person").save()
        interest = ResearchInterest(name="interest").save()
        institute = Institute(name="institute").save()
        fac = Faculty(name="faculty").save()
        dep = Department(name="department").save()
        role = Role(name="role").save()
        offered_exp = Expertise(name="offered E").save()
        wanted_exp = Expertise(name="wanted E").save()
        # relationships
        person1.interests.connect(interest)
        person1.institutes.connect(institute)

    def test_missing_parameter(self):
        response = self.client.get("/expertise/graph")
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.json())

        response = self.client.get("/expertise/graph?person=")
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.json())

    def test_person_not_exist(self):
        response = self.client.get("/expertise/graph?person=abc")
        self.assertEqual(response.status_code, 200)
        self.assertEqual("person does not exist", response.json()["error"])

    def test_data(self):
        person = Person.nodes.get(name="Adviso")
        response = self.client.get("/expertise/graph?person=" + person.pk)
        data = response.json()["graph"]
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(data["nodes"]) > 1)
        self.assertTrue(len(data["relationships"]) > 1)
        for node in data["nodes"]:
            self.assertIn("id", node)
            self.assertIn("properties", node)
            self.assertIn("labels", node)

        for rel in data["relationships"]:
            self.assertIn("startNode", rel)
            self.assertIn("endNode", rel)
            self.assertIn("type", rel)
