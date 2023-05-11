from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from neomodel import Q, DoesNotExist

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
        "persons": {
            "class": "person",
            "group": "Persons",
            "options": Person.nodes.all(),
        },
        "interests": {
            "class": "interest",
            "group": "Interests",
            "options": ResearchInterest.nodes.all(),
        },
        "institutes": {
            "class": "institute",
            "group": "Institutes",
            "options": Institute.nodes.all(),
        },
        "faculties": {
            "class": "faculty",
            "group": "Faculties",
            "options": Faculty.nodes.all(),
        },
        "departments": {
            "class": "department",
            "group": "Departments",
            "options": Department.nodes.all(),
        },
        "advisors": {
            "class": "person",
            "group": "Advisors",
            "options": Person.nodes.all(),
        },
        "roles": {
            "class": "role",
            "group": "Roles",
            "options": Role.nodes.all(),
        },
        "offered_expertise": {
            "class": "expertise",
            "group": "Offered expertise",
            "options": Expertise.nodes.all(),
        },
        "wanted_expertise": {
            "class": "expertise",
            "group": "Wanted expertise",
            "options": Expertise.nodes.all(),
        },
    }
    return suggestions

def person_contains_value(person, value) -> bool:
    # use (person.property or "") in case a person does not have that property
    return (value in (person.name or "").lower() or
            value in (person.title or "").lower() or
            value in (person.email or "").lower())

def person_or_connected_node_contains_value(person, value) -> bool:
    # in this condition I don't check if email contains the value
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

def convert_node_list(nodes) -> list[tuple]:
    return [{"name": node.name, "pk": node.pk} for node in nodes]

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
        data["interests"] = convert_node_list(person.interests.all())
        data["institutes"] = convert_node_list(person.institutes.all())
        data["faculties"] = convert_node_list(person.faculties.all())
        data["departments"] = convert_node_list(person.departments.all())
        data["roles"] = convert_node_list(person.roles.all())
        data["offered"] = convert_node_list(person.offered_expertise.all())
        data["wanted"] = convert_node_list(person.wanted_expertise.all())
        data["advisors"] = [{"name": adv.name, "title": adv.title, "pk": adv.pk}
                            for adv in person.advisors.all()]
        entries.append(data)

    return entries

def get_filtered_persons(search_param: str) -> list[dict]:
    # TODO: optimize so I don't get all values of all persons twice
    # maybe just use a cypher query
    persons = Person.nodes.all()
    matching_persons = []
    if search_param == "":
        matching_persons = persons
    else:
        for person in persons:
            if person_or_connected_node_contains_value(person, search_param):
                matching_persons.append(person)

    return get_all_person_values(matching_persons)

def format_nodes_for_graph(nodes):
    # the primary keys instead of node ids are used because it's
    # needed for frontend functionality
    return [{"id": node.get("pk"),
            "properties": {
                "name": node.get("name"),
                # TODO: maybe also add persons' titles
            },
            "labels": list(node.labels)}
            for node in nodes]

def format_rels_for_graph(rels):
    return [{"startNode": rel.nodes[0].get("pk"),
            "endNode": rel.nodes[1].get("pk"),
            "type": rel.type}
            for rel in rels]

def get_graph_data(person: Person):
    nodes, rels = person.all_connected()
    graph_data = {}
    graph_data["nodes"] = format_nodes_for_graph(nodes)
    # append the person that the graph is for
    person_data = {
        "id": person.pk,
        "properties": {
            "name": person.name
        },
        "labels": ["Person"],
    }
    graph_data["nodes"].append(person_data)
    graph_data["relationships"] = format_rels_for_graph(rels)
    return graph_data

def get_nav_active_marker() -> dict:
    # maybe this should be a constant variable somewhere instead?
    return {
        "class": "active",
        "aria": "aria-current=page",
    }

# VIEWS BELOW

def index(request):
    context = {
        "suggestions": get_suggestions(),
        "nav_home": get_nav_active_marker(),
    }
    return render(request, "expertise/index.html", context)

def edit(request):
    context = {
        "nav_edit": get_nav_active_marker(),
    }
    return render(request, "expertise/edit.html", context)

def persons_api(request):
    data = {}
    if "search" not in request.GET:
        data["error"] = "missing parameter: search"
        return JsonResponse(data)

    search_param = request.GET.get("search")
    persons_data = get_filtered_persons(search_param.lower())
    data["persons"] = persons_data
    return JsonResponse(data)

def graph_api(request):
    data = {}
    person_id = request.GET.get("person")
    if person_id in (None, ""):
        # maybe different errors for missing parameter and missing value
        data["error"] = "missing parameter: person"
        return JsonResponse(data)

    try:
        person_node = Person.nodes.get(pk=person_id)
    except DoesNotExist:
        data["error"] = "person does not exist"
        return JsonResponse(data)

    graph_data = get_graph_data(person_node)
    data["graph"] = graph_data
    return JsonResponse(data)
