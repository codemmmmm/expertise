import os
import sys
from django.test import TestCase
from neomodel import config, db, clear_neo4j_database, install_all_labels, DoesNotExist

from expertise.models import (
    Person,
    ResearchInterest,
    Institute,
    Faculty,
    Department,
    Role,
    Expertise
)
from expertise.forms import EditForm
from .views import *

# e.g. the form would still use the non-test database because it is
# initialized before the test is run
url_with_database = os.environ['NEO4J_BOLT_URL']
split_url = url_with_database.split("/")
split_url[-1] = "test"
test_url = "/".join(split_url)
db.set_connection(test_url)
with open(os.devnull, "w") as f:
    install_all_labels(f)

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

class EditTestcase(TestCase):
    def setUp(self):
        clear_neo4j_database(db)

    def test_initial_form_values(self):
        # nodes
        person1 = Person(name="Jake", email="a@a.com", title="title").save()
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
        person1.faculties.connect(fac)
        person1.departments.connect(dep)
        person1.roles.connect(role)
        person1.offered_expertise.connect(offered_exp)
        person1.wanted_expertise.connect(wanted_exp)
        person1.advisors.connect(person2)

        response = self.client.get("/expertise/edit-form?id=" + person1.pk)
        form = response.context["form"]
        self.assertEqual(form.initial["email"], "a@a.com")
        self.assertEqual(form.initial["title"], "title")
        self.assertEqual(form.initial["interests"], [interest.pk])
        self.assertEqual(form.initial["institutes"], [institute.pk])
        self.assertEqual(form.initial["faculties"], [fac.pk])
        self.assertEqual(form.initial["departments"], [dep.pk])
        self.assertEqual(form.initial["advisors"], [person2.pk])
        self.assertEqual(form.initial["roles"], [role.pk])
        self.assertEqual(form.initial["offered"], [offered_exp.pk])
        self.assertEqual(form.initial["wanted"], [wanted_exp.pk])

    def test_required_email(self):
        data = {
            "person": "",
            "email": "",
            }
        form = EditForm(data)
        self.assertTrue(form.has_error("email", "required"))

        data = {
            "person": "",
            "email": "hi@hi.de",
            }
        form = EditForm(data)
        self.assertFalse(form.has_error("email"))

    def test_new_entry(self):
        """test that the form field doesn't cause errors when a new choice is added"""
        data = {
            "personId": "",
            "name": "name",
            "email": "x@x.de",
            "interest": ["new entry not in field's choices"],
            }
        form = EditForm(data)
        self.assertFalse(form.errors)

    def test_form_no_relation_changes(self):
        # nodes
        person1 = Person(name="Jake", email="a@a.com", title="title").save()
        person2 = Person(name="Person").save()
        interest = ResearchInterest(name="interest").save()
        offered_exp = Expertise(name="expertise").save()
        wanted_exp = offered_exp
        # relationships
        person1.interests.connect(interest)
        person1.offered_expertise.connect(offered_exp)
        person1.wanted_expertise.connect(wanted_exp)

        post_data = {
            "personId": person1.pk,
            "name": person1.name,
            "email": "b@b.com",
            "title": "",
            "interests": [interest.pk],
            "offered": [offered_exp.pk],
            "wanted": [wanted_exp.pk],
        }
        self.client.post("/expertise/edit-form", post_data)
        person1.refresh()
        self.assertEqual(person1.email, "b@b.com")
        self.assertEqual(person1.interests.all()[0], interest)
        self.assertEqual(len(person1.interests.all()), 1)
        self.assertEqual(person1.offered_expertise.all()[0], person1.wanted_expertise.all()[0])

    def test_form_changed_relations(self):
        """test disconnecting an assigned node, adding an existing node, adding a new node"""
        # nodes
        person = Person(name="Jake", email="a@a.com", title="title").save()
        offered_exp = Expertise(name="offered exp").save()
        wanted_exp = Expertise(name="wanted exp").save()
        unconnected_exp = Expertise(name="unconnected exp").save()
        # relationships
        person.offered_expertise.connect(offered_exp)
        person.wanted_expertise.connect(wanted_exp)

        post_data = {
            "personId": person.pk,
            "name": person.name,
            "email": person.email,
            "title": person.title,
            "offered": [offered_exp.pk, unconnected_exp.pk],
            "wanted": ["new exp"],
        }
        response = self.client.post("/expertise/edit-form", post_data)
        person.refresh()
        offered = person.offered_expertise.all()
        self.assertEqual(len(offered), 2)
        self.assertIn(offered_exp, offered)
        self.assertIn(unconnected_exp, offered)
        wanted = person.wanted_expertise.all()
        self.assertEqual(len(wanted), 1)
        self.assertEqual(wanted[0].name, "new exp")
        self.assertEqual(response.status_code, 200)

        get_response = self.client.get("/expertise/edit-form?id=" + person.pk)
        form = get_response.context["form"]
        # test that the select options in the form were updated
        expertise_options = [x for x, _ in form.fields["wanted"].choices]
        new_expertise = Expertise.nodes.get(name="new exp")
        self.assertIn(new_expertise.pk, expertise_options)

    def test_new_person(self):
        post_data = {
            "personId": "",
            "name": "new person",
            "email": "a@a.com",
            "offered": ["new expertise"],
        }
        self.client.post("/expertise/edit-form", post_data)
        person = Person.nodes.get(name="new person")
        self.assertIsNotNone(person)
        self.assertEqual(person.offered_expertise.all()[0].name, "new expertise")

    def test_duplicate_email(self):
        person = Person(name="ash", email="a@a.com").save()
        person2 = Person(name="rock", email="b@b.com").save()

        post_data = {
            "personId": "",
            "name": "new name",
            "email": "a@a.com",
        }
        response = self.client.post("/expertise/edit-form", post_data)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["email"][0]["message"], "This email is already in use.")

        post_data = {
            "personId": person2.pk,
            "name": person2.name,
            "email": "a@a.com",
        }
        response = self.client.post("/expertise/edit-form", post_data)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["email"][0]["message"], "This email is already in use.")

    def test_entity_name_restrictions(self):
        # TODO: extend tests if more restrictions are introduced
        person = Person(name="Jake", email="a@a.com", title="title").save()
        post_data = {
            "personId": person.pk,
            "name": person.name,
            "email": person.email,
            "offered": [" new expertise "],
        }
        self.client.post("/expertise/edit-form", post_data)
        self.assertEqual(person.offered_expertise.all()[0].name, "new expertise")

    def test_invalid_form(self):
        # TODO: test with incorrect personId?
        post_data = {
            "personId": "person name",
        }
        response = self.client.post("/expertise/edit-form", post_data)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["name"][0]["message"], "This field is required.")
        self.assertEqual(response.json()["email"][0]["message"], "This field is required.")
        self.assertEqual(len(response.json()), 2)

    # test adding new person with same name as existing person?
