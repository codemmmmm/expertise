from django.db import models
from neomodel import StringProperty, EmailProperty, RelationshipTo, UniqueIdProperty, ArrayProperty
from django_neomodel import DjangoNode
from neo4j.graph import Node

# Neo4j

class ResearchInterest(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()
    alternatives = ArrayProperty(StringProperty())

    class Meta:
        app_label = "expertise"

class Institute(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()
    alternatives = ArrayProperty(StringProperty())

    class Meta:
        app_label = "expertise"
        verbose_name = "institution"

class Faculty(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()
    alternatives = ArrayProperty(StringProperty())

    class Meta:
        app_label = "expertise"
        verbose_name = "faculty/institute/center"
        verbose_name_plural = "faculties/institutes/centers"

class Department(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()
    alternatives = ArrayProperty(StringProperty())

    class Meta:
        app_label = "expertise"
        verbose_name = "department/group"
        verbose_name_plural = "departments/groups"

class Expertise(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()
    alternatives = ArrayProperty(StringProperty())

    class Meta:
        app_label = "expertise"
        verbose_name_plural = "expertise"

class Role(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()
    alternatives = ArrayProperty(StringProperty())

    class Meta:
        app_label = "expertise"

class Person(DjangoNode):
    def all_connected(self, inflate: bool=False) -> dict[str, list[DjangoNode | Node]]:
        """
        returns dictionary of all nodes directly connected to the person except the
        people the person advises

        Args:
            inflate (bool, optional): if the node should be inflated to a DjangoNode
        """
        person_data: dict[str, list[DjangoNode | Node]] = {
            "interests": [],
            "institutes": [],
            "faculties": [],
            "departments": [],
            "roles": [],
            "offered": [],
            "wanted": [],
            "advisors": [],
        }
        results, _ = self.cypher("MATCH (p:Person)-[r]-(n) WHERE id(p)=$self RETURN r, n")
        for rel, node in results:
            label = list(node.labels)[0]
            # TODO: turn into match?
            if label == "ResearchInterest":
                person_data["interests"].append(ResearchInterest.inflate(node) if inflate else node)
            elif label == "Institute":
                person_data["institutes"].append(Institute.inflate(node) if inflate else node)
            elif label == "Faculty":
                person_data["faculties"].append(Faculty.inflate(node) if inflate else node)
            elif label == "Department":
                person_data["departments"].append(Department.inflate(node) if inflate else node)
            elif label == "Role":
                person_data["roles"].append(Role.inflate(node) if inflate else node)
            # all person nodes here should be advisors
            elif label == "Person":
                # ignore the person nodes that are advised by self
                if rel.nodes[0] != node:
                    person_data["advisors"].append(Person.inflate(node) if inflate else node)
            elif rel.type == "OFFERS":
                person_data["offered"].append(Expertise.inflate(node) if inflate else node)
            elif rel.type == "WANTS":
                person_data["wanted"].append(Expertise.inflate(node) if inflate else node)
            else:
                raise ValueError
        return person_data

    name = StringProperty(required=True, max_length=120)
    # not required because people mentioned as advisors might not have any data entered
    email = EmailProperty(unique_index=True)
    title = StringProperty(max_length=60, default="")
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

# SQLite

def default_list() -> list[str]:
    return []

class EditSubmission(models.Model):
    person_id = models.CharField(max_length=30, null=True, unique=True)
    person_id_new = models.CharField(max_length=30, null=True, unique=True, blank=False)
    person_name = models.CharField(max_length=80, default="", null=False)
    person_name_new = models.CharField(max_length=80, default="", null=False)
    person_email = models.EmailField(null=False, default="")
    # maybe unique should be false
    person_email_new = models.EmailField(null=False, blank=False, unique=True)
    person_title = models.CharField(max_length=40, default="", null=False)
    person_title_new = models.CharField(max_length=40, default="", null=False)
    interests = models.JSONField(null=False, default=default_list)
    interests_new = models.JSONField(null=False, default=default_list)
    institutes = models.JSONField(null=False, default=default_list)
    institutes_new = models.JSONField(null=False, default=default_list)
    faculties = models.JSONField(null=False, default=default_list)
    faculties_new = models.JSONField(null=False, default=default_list)
    departments = models.JSONField(null=False, default=default_list)
    departments_new = models.JSONField(null=False, default=default_list)
    advisors = models.JSONField(null=False, default=default_list)
    advisors_new = models.JSONField(null=False, default=default_list)
    roles = models.JSONField(null=False, default=default_list)
    roles_new = models.JSONField(null=False, default=default_list)
    offered = models.JSONField(null=False, default=default_list)
    offered_new = models.JSONField(null=False, default=default_list)
    wanted = models.JSONField(null=False, default=default_list)
    wanted_new = models.JSONField(null=False, default=default_list)

# the implicitly created primary key is used as the shortened value
class ShareParameters(models.Model):
    parameters = models.CharField(max_length=1000, unique=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
