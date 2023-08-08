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
    Expertise,
    EditSubmission,
)
from expertise.forms import EditForm
from expertise.views import *

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

    def test_missing_parameter(self):
        response = self.client.get("/expertise/graph")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

        response = self.client.get("/expertise/graph?id=")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_person_not_exist(self):
        response = self.client.get("/expertise/graph?id=abc")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual({
            "nodes": [],
            "relationships": [],
        }, data["graph"])

    def test_data(self):
        # nodes
        person1 = Person(title="Prof", name="Adviso", comment="I am hiring").save()
        person2 = Person(name="Person").save()
        interest = ResearchInterest(name="interest").save()
        institute = Institute(name="institute").save()
        fac = Faculty(name="faculty").save()
        dep = Department(name="department").save()
        role = Role(name="role").save()
        expertise1 = Expertise(name="offered E").save()
        expertise2 = Expertise(name="wanted E").save()
        # relationships
        person1.interests.connect(interest)
        person1.institutes.connect(institute)
        person1.offered_expertise.connect(expertise1)
        person1.wanted_expertise.connect(expertise1)

        response = self.client.get("/expertise/graph?id=" + person1.pk)
        data = response.json()["graph"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["nodes"]), 4)
        self.assertEqual(len(data["relationships"]), 4)
        for node in data["nodes"]:
            self.assertIn("id", node)
            self.assertIn("properties", node)
            self.assertIn("labels", node)

        for rel in data["relationships"]:
            self.assertIn("startNode", rel)
            self.assertIn("endNode", rel)
            self.assertIn("type", rel)

def get_submission_from_person_id(id: str) -> EditSubmission:
    return EditSubmission.objects.get(person_id_new=id)

def get_submission_from_person_email(email: str, name: str) -> EditSubmission:
    return EditSubmission.objects.get(person_email_new=email, person_name_new=name)

def get_post_data(submission: EditSubmission, action) -> dict[str, str | Sequence[str]]:
    property_and_key_names = (
        ("person_name", "name"),
        ("person_email", "email"),
        ("person_title", "title"),
        ("interests", "interests"),
        ("institutes", "institutes"),
        ("faculties", "faculties"),
        ("departments", "departments"),
        ("advisors", "advisors"),
        ("roles", "roles"),
        ("offered", "offered"),
        ("wanted", "wanted"),
    )
    post_data = {}
    for property_name, key in property_and_key_names:
            prefixed_key = str(submission.id) + "new-" + key
            post_data[prefixed_key] = getattr(submission, property_name + "_new")
    post_data["action"] = action
    post_data["submissionId"] = submission.id
    return post_data

class EditTestCase(TestCase):
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

        submission = get_submission_from_person_id(person1.pk)
        submission_data = get_post_data(submission, "approve")
        response = self.client.post("/expertise/approve", submission_data)

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

        submission = get_submission_from_person_id(person.pk)
        submission_data = get_post_data(submission, "approve")
        response = self.client.post("/expertise/approve", submission_data)

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

        submission = get_submission_from_person_email("a@a.com", "new person")
        submission_data = get_post_data(submission, "approve")
        response = self.client.post("/expertise/approve", submission_data)

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

        submission = get_submission_from_person_id(person.pk)
        submission_data = get_post_data(submission, "approve")
        response = self.client.post("/expertise/approve", submission_data)

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

    def test_new_person_rejected(self):
        post_data = {
            "personId": "",
            "name": "new person",
            "email": "a@a.com",
            "offered": ["new expertise"],
        }
        self.client.post("/expertise/edit-form", post_data)
        post_data = {
            "personId": "",
            "name": "other name",
            "email": "b@b.com",
            "offered": ["other expertise"],
        }
        self.client.post("/expertise/edit-form", post_data)

        submission = get_submission_from_person_email("a@a.com", "new person")
        submission_data = get_post_data(submission, "reject")
        self.client.post("/expertise/approve", submission_data)

        submission = get_submission_from_person_email("b@b.com", "other name")
        submission_data = get_post_data(submission, "approve")
        self.client.post("/expertise/approve", submission_data)

        self.assertEqual(len(Person.nodes.all()), 1)
        self.assertEqual(len(Expertise.nodes.all()), 1)
        self.assertEqual(Person.nodes.all()[0].email, "b@b.com")

    def test_duplicate_entity_name(self):
        interest = ResearchInterest(name="new interest").save()
        institute = Institute(name="new institute").save()
        post_data = {
            "personId": "",
            "name": "new person",
            "email": "a@a.com",
            "interests": [interest.pk, "new interest"],
            "institutes": ["new institute", institute.pk],
            "offered": ["new expertise", "new expertise"],
        }
        response = self.client.post("/expertise/edit-form", post_data)

        submission = get_submission_from_person_email("a@a.com", "new person")
        submission_data = get_post_data(submission, "approve")
        self.client.post("/expertise/approve", submission_data)

        self.assertEqual(len(ResearchInterest.nodes.all()), 1)
        self.assertEqual(len(Expertise.nodes.all()), 1)

class EditSubmissionTestCase(TestCase):
    def setUp(self):
        clear_neo4j_database(db)

    def test_value_comparison(self):
        self.assertTrue(is_same_string_or_list("abc", "abc"))
        self.assertTrue(is_same_string_or_list(["abc"], ["abc"]))
        self.assertFalse(is_same_string_or_list("ab", "abc"))
        self.assertFalse(is_same_string_or_list(["ab"], ["abc"]))
        self.assertFalse(is_same_string_or_list(["abc"], ["abc", "ab"]))

        data1 = {
            "key1": "a",
            "key2": ["a"],
            "key3": "",
            "key4": [],
        }
        data2 = {
            "key1": "a",
            "key2": ["a"],
            "key3": "",
            "key4": [],
        }
        self.assertTrue(is_same_data(data1, data2))

        data1 = {
            "key1": None,
        }
        data2 = {
            "key1": [],
        }
        self.assertRaises(TypeError)

        data1 = {
            "key1": "a",
            "key2": ["a", "b"],
        }
        data2 = {
            "key1": "a",
            "key2": ["a"],
        }
        self.assertFalse(is_same_data(data1, data2))

        data1 = {
            "key1": "a",
        }
        data2 = {
            "key1": "b",
        }
        self.assertFalse(is_same_data(data1, data2))

    def test_get_submission_existing_person(self):
        person = Person(name="Jake", email="a@a.com").save()
        post_data = {
            "personId": person.pk,
            "name": person.name,
            "email": person.email,
            "title": "new title",
        }
        self.client.post("/expertise/edit-form", post_data)
        submission = get_submission_or_none(person)
        self.assertIsNotNone(submission)

    def test_get_submission_existing_person_email_change(self):
        person = Person(name="Jake", email="a@a.com").save()
        post_data = {
            "personId": person.pk,
            "name": person.name,
            "email": "b@b.com",
            "title": "new title",
        }
        self.client.post("/expertise/edit-form", post_data)
        submission = get_submission_or_none(person)
        self.assertIsNotNone(submission)

    def test_get_submission_new_person(self):
        name = "Jake"
        email = "a@a.com"
        post_data = {
            "personId": "",
            "name": name,
            "email": email,
        }
        self.client.post("/expertise/edit-form", post_data)
        # person should not be saved
        person = Person(name=name, email=email)
        submission = get_submission_or_none(person)
        self.assertIsNotNone(submission)

    def test_get_submission_new_person_email_change(self):
        name = "Jake"
        email = "a@a.com"
        post_data = {
            "personId": "",
            "name": name,
            "email": email,
        }
        self.client.post("/expertise/edit-form", post_data)
        # simulates a request where the email was changed
        person = Person(name=name, email="b@b.com")
        submission = get_submission_or_none(person)
        self.assertIsNone(submission)

    def test_save_new_submission_with_change(self):
        person1 = Person(name="Jake", email="a@a.com").save()
        exp1 = Expertise(name="expertise").save()
        exp2 = Expertise(name="expertise 2").save()
        person1.offered_expertise.connect(exp1)
        person1.offered_expertise.connect(exp2)
        data = {
            "name": person1.name,
            "email": "b@b.com",
            "title": person1.title,
            "offered": [exp1.pk, exp2.pk, "new offered"],
            "institutes": ["institute"],
        }

        form = EditForm(data)
        form.is_valid()
        save_submission(person1, form.cleaned_data)
        submission = EditSubmission.objects.first()
        self.assertEqual(submission.person_id, person1.pk)
        self.assertEqual(submission.person_id_new, person1.pk)
        self.assertEqual(submission.person_name_new, person1.name)
        self.assertEqual(submission.person_email_new, "b@b.com")
        self.assertEqual(submission.person_title_new, "")
        self.assertCountEqual(submission.offered, [exp1.pk, exp2.pk])
        self.assertCountEqual(submission.offered_new, [exp1.pk, exp2.pk, "new offered"])
        self.assertCountEqual(submission.institutes_new, ["institute"])

        data = {
            "name": person1.name,
            "email": "b@b.com",
            "title": person1.title,
            "offered": [exp1.pk, exp2.pk, "new offered"],
            "institutes": [],
        }
        form = EditForm(data)
        form.is_valid()
        save_submission(person1, form.cleaned_data)
        submission = EditSubmission.objects.first()
        self.assertEqual(submission.institutes_new, [])

    def test_new_submission_no_change(self):
        person1 = Person(name="Jake", email="a@a.com").save()
        exp1 = Expertise(name="expertise").save()
        exp2 = Expertise(name="expertise 2").save()
        person1.offered_expertise.connect(exp1)
        person1.offered_expertise.connect(exp2)
        data = {
            "name": person1.name,
            "email": person1.email,
            "offered": [exp1.pk, exp2.pk],
        }

        form = EditForm(data)
        form.is_valid()
        save_submission(person1, form.cleaned_data)
        self.assertEqual(len(EditSubmission.objects.all()), 0)

    def test_change_existing_submission_existing_person(self):
        person1 = Person(name="Jake", email="a@a.com").save()
        exp1 = Expertise(name="expertise").save()
        exp2 = Expertise(name="expertise 2").save()
        person1.offered_expertise.connect(exp1)
        person1.offered_expertise.connect(exp2)
        # new submission
        data = {
            "name": person1.name,
            "email": person1.email,
            "offered": [exp1.pk, exp2.pk, "new expertise"],
        }

        form = EditForm(data)
        form.is_valid()
        save_submission(person1, form.cleaned_data)

        # change previous submission
        data = {
            "name": "different name",
            "email": person1.email,
            "offered": [exp1.pk, exp2.pk],
        }

        form = EditForm(data)
        form.is_valid()
        save_submission(person1, form.cleaned_data)
        submissions = EditSubmission.objects.all()
        self.assertEqual(len(submissions), 1)
        submission = submissions.first()
        self.assertEqual(submission.person_name_new, "different name")
        self.assertCountEqual(submission.offered, [exp1.pk, exp2.pk])
        self.assertCountEqual(submission.offered_new, [exp1.pk, exp2.pk])

    def test_change_existing_submission_existing_person_no_difference(self):
        person1 = Person(name="Jake", email="a@a.com").save()
        exp1 = Expertise(name="expertise").save()
        exp2 = Expertise(name="expertise 2").save()
        person1.offered_expertise.connect(exp1)
        person1.offered_expertise.connect(exp2)
        # new submission
        data = {
            "name": "different name",
            "email": person1.email,
            "offered": [exp1.pk, exp2.pk, "new expertise"],
        }

        form = EditForm(data)
        form.is_valid()
        save_submission(person1, form.cleaned_data)

        # change previous submission
        data = {
            "name": "Jake", # original name
            "email": person1.email,
            "offered": [exp1.pk, exp2.pk],
        }

        form = EditForm(data)
        form.is_valid()
        save_submission(person1, form.cleaned_data)
        submissions = EditSubmission.objects.all()
        self.assertEqual(len(submissions), 0)

    def test_change_existing_submission_new_person(self):
        exp1 = Expertise(name="expertise").save()
        # new submission without saving nodes
        post_data = {
            "name": "Jake",
            "email": "test@test.de",
            "offered": [exp1.pk, "exp2"],
        }
        self.client.post("/expertise/edit-form", post_data)
        self.assertEqual(len(Person.nodes.all()), 0)
        submission = EditSubmission.objects.first()
        self.assertCountEqual(submission.offered, [])
        self.assertCountEqual(submission.offered_new, [exp1.pk, "exp2"])

        # change previous submission
        post_data = {
            "name": "Jake",
            "email": "test@test.de",
            "offered": ["exp2"],
        }
        self.client.post("/expertise/edit-form", post_data)
        self.assertEqual(len(Person.nodes.all()), 0)
        submissions = EditSubmission.objects.all()
        self.assertEqual(len(submissions), 1)
        submission = submissions.first()
        self.assertCountEqual(submission.offered, [])
        self.assertCountEqual(submission.offered_new, ["exp2"])

    def test_save_submission_no_old_email(self):
        person = Person(name="Hans").save()
        post_data = {
            "personId": person.pk,
            "name": person.name,
            "email": "test@test.de",
        }
        self.client.post("/expertise/edit-form", post_data)
        submission = EditSubmission.objects.first()
        self.assertEqual(submission.person_email, "")
        self.assertEqual(submission.person_email_new, "test@test.de")

    def test_get_submissions_data(self):
        person = Person(name="Jake", email="a@a.com").save()
        exp1 = Expertise(name="expertise").save()
        exp2 = Expertise(name="expertise 2").save()
        person.offered_expertise.connect(exp1)
        person.offered_expertise.connect(exp2)
        post_data = {
            "personId": person.pk,
            "name": person.name,
            "email": person.email,
            "offered": [exp1.pk, exp2.pk, "new expertise"],
        }
        response = self.client.post("/expertise/edit-form", post_data)

        post_data = {
            "personId": "",
            "name": "Lisa",
            "email": "test@test.de",
            "offered": ["expertise3"],
        }
        response = self.client.post("/expertise/edit-form", post_data)

        submissions = EditSubmission.objects.all().order_by("id")
        submissions_data = get_submissions_forms(submissions)
        self.assertEqual(len(submissions_data), 2)

        submission_data1 = submissions_data[0]
        name_field_index = 0
        faculties_field_index = 5
        expertise_field_index = 9
        # index 0 is the new field
        self.assertCountEqual(submission_data1["data"][name_field_index][0].value(), person.name)
        self.assertCountEqual(submission_data1["data"][expertise_field_index][0].value(), [exp1.pk, exp2.pk, "new expertise"])
        submission_data2 = submissions_data[1]
        self.assertCountEqual(submission_data1["data"][faculties_field_index][0].value(), [])

    # test with too long entity names (max length validation for form)
    # test submission for setting new and existing person's email the same as existing person

    # test graph api for two connections between two nodes, e.g. person A -> expertise 1 twice (wanted/offered)


