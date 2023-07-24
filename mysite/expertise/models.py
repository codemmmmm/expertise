from typing import Any
from neomodel import StringProperty, EmailProperty, RelationshipTo, UniqueIdProperty
from django_neomodel import DjangoNode

class ResearchInterest(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()

    class Meta:
        app_label = "expertise"

class Institute(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()

    class Meta:
        app_label = "expertise"

class Faculty(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()

    class Meta:
        app_label = "expertise"
        verbose_name_plural = "faculties"

class Department(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()

    class Meta:
        app_label = "expertise"

class Expertise(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()

    class Meta:
        app_label = "expertise"
        verbose_name_plural = "expertise"

class Role(DjangoNode):
    name = StringProperty(unique_index=True, required=True, max_length=200)
    pk = UniqueIdProperty()

    class Meta:
        app_label = "expertise"

class Person(DjangoNode):
    def all_connected(self, inflate: bool=False) -> dict[str, list[Any]]:
        """
        returns dictionary of all nodes directly connected to the person except the
        people the person advises

        Args:
            inflate (bool, optional): if the node should be inflated to a Node object. Defaults to False.
        """
        person_data = {
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
