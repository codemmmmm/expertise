from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from neomodel import Q, db
from neo4j import GraphDatabase
import os
import requests

from expertise.models import (
    Person,
    ResearchInterest,
    Institute,
    Faculty,
    Department,
    Role,
    Expertise
)

def get_suggestions() -> dict:
    # TODO:
    # advisors = filter only people that advise someone
    # offered = filter only what is offered
    # wanted = filter only what is wanted
    # maybe with cypher query or somehow filtering nodesets, distinct?
    # otherwise, save all persons and expertise in a variable instead of searching twice

    suggestions = {
        "Persons": Person.nodes.all(),
        "Interests": ResearchInterest.nodes.all(),
        "Institutes": Institute.nodes.all(),
        "Faculties": Faculty.nodes.all(),
        "Departments": Department.nodes.all(),
        "Advisors": Person.nodes.all(),
        "Roles": Role.nodes.all(),
        "Offered expertise": Expertise.nodes.all(),
        "Wanted expertise": Expertise.nodes.all(),
    }
    return suggestions

def person_contains_value(person, value) -> bool:
    # use (person.property or "") in case a person does not have that property
    return (value in (person.name or "").lower() or
            value in (person.title or "").lower() or
            value in (person.email or "").lower())

def person_or_connected_node_contains_value(person, value) -> bool:
    # in this condition i don't check if email contains the value
    # because this causes an error (caused by bug in neomodel I believe)
    person_node_condition = (Q(name__icontains=value) |
        Q(title__icontains=value))

    return (person_contains_value(person, value) or
        person.interests.filter(name__icontains=value) or
        person.institutes.filter(name__icontains=value) or
        person.faculties.filter(name__icontains=value) or
        person.departments.filter(name__icontains=value) or
        person.roles.filter(name__icontains=value) or
        person.offered_expertise.filter(name__icontains=value) or
        person.wanted_expertise.filter(name__icontains=value) or
        person.advisors.filter(person_node_condition))

def get_all_person_values(persons: list) -> list[dict]:
    entries = []
    for person in persons:
        data = {}
        data["person"] = {
            "name": person.name,
            "title": person.title,
            "email": person.email,
            "pk": person.pk,
        }
        data["interests"] = [inte.name for inte in person.interests.all()]
        data["institutes"] = [inst.name for inst in person.institutes.all()]
        data["faculties"] = [fac.name for fac in person.faculties.all()]
        data["departments"] = [dep.name for dep in person.departments.all()]
        data["roles"] = [role.name for role in person.roles.all()]
        data["offered"] = [off.name for off in person.offered_expertise.all()]
        data["wanted"] = [wanted.name for wanted in person.wanted_expertise.all()]
        data["advisors"] = [adv.title + " " + adv.name if adv.title else adv.name for adv in person.advisors.all()]
        entries.append(data)

    return entries

def get_filtered_persons(search_param: str) -> list[dict]:
    # maybe just use a written cypher query
    persons = Person.nodes.all()
    matching_persons = []
    if search_param == "":
        matching_persons = persons
    else:
        for person in persons:
            if person_or_connected_node_contains_value(person, search_param):
                print(person)
                matching_persons.append(person)

    return get_all_person_values(matching_persons)

def get_all_close_relations(tx, person_id):
    records = []
    result = tx.run("MATCH (p:Person {pk:$pk})-[r*1..2]-(n)"
                    "RETURN p, r, n", pk=person_id)

    for record in result:
        records.append(record["r"])
    return records

def get_graph_data(person_id: str):
    # TODO: improve this weird splitting
    full_url = os.environ['NEO4J_BOLT_URL']
    url = full_url[0:7] + full_url[-14:]
    user = "neo4j"
    password = full_url.split("neo4j:")[1][:-15]
    # print(url)
    # print(user)
    # print(password)

    with GraphDatabase.driver(url, auth=(user, password), database="expertise") as driver:
        with driver.session() as session:
            graph = session.read_transaction(get_all_close_relations, person_id)
            #for record in graph:
             #   print(record)

    # data = {
    #     "statements": [
    #         {
    #             "statement": "MATCH (n)-[r]-(m) RETURN n, r, m LIMIT 5;",
    #             "resultDataContents": ["graph"],
    #         },
    #     ]
    # }

    # r = requests.post("http://localhost:7474/db/expertise/tx", auth=(user, password), json=data)
    # return r.json()

def test():
    # m = Person(name='Moritz').save()
    # s = Person(name='Siavash').save()
    # r = m.advisors.connect(s)
    # ResearchInterest(name='AI').save()
    # ResearchInterest(name='AI').save()
    # Role(name='Programmer').save()
    # Expertise(name='python').save()
    # Institute(name='TUD').save()
    # Faculty(name='ZIH').save()
    # Department(name='CompSci').save()

    # for p in Person.nodes.all():
    #    print(p)
    pass

# VIEWS

def index(request):
    context = {
        "suggestions": get_suggestions(),
    }
    return render(request, 'expertise/index.html', context)

def edit(request):
    return render(request, 'expertise/edit.html')

def persons(request):
    # TODO: optimize so I don't get all values of all persons twice
    search_param = request.GET.get("search", "")
    persons_data = get_filtered_persons(search_param.lower())
    data = {
        "persons": persons_data,
    }
    return JsonResponse(data)

def graph(request):
    graph_data = get_graph_data("x")
    #print(results)

    # for item in results:
    #     for x in item:
    #         print(x)
    #     print("\n")
    data = {
        "graph": graph_data,
    }
    return JsonResponse(data)
    #return HttpResponse(data)
