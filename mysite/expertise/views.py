from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from neomodel import DoesNotExist, db

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
    """returns data of all nodes

    the lists with persons and expertise contain all persons/expertise entries.
    this means that e.g. the offered expertise list can have an entry of an expertise node
    that is only used as wanted expertise
    """
    person_nodes = Person.nodes.all()
    expertise_nodes = Expertise.nodes.all()
    suggestions = {
        "persons": {
            "class": "person",
            "group": "Persons",
            "options": person_nodes,
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
            "options": person_nodes,
        },
        "roles": {
            "class": "role",
            "group": "Roles",
            "options": Role.nodes.all(),
        },
        "offered_expertise": {
            "class": "expertise",
            "group": "Offered expertise",
            "options": expertise_nodes,
        },
        "wanted_expertise": {
            "class": "expertise",
            "group": "Wanted expertise",
            "options": expertise_nodes,
        },
    }
    return suggestions

def convert_node_list(nodes) -> list[tuple]:
    return [{"name": node.get("name"), "pk": node.get("pk")} for node in nodes]

def get_all_person_data(persons: list) -> list[dict]:
    entries = []
    for person in persons:
        data = person.all_connected()
        data["person"] = {
                "name": person.name,
                "title": person.title,
                "email": person.email,
                "pk": person.pk,
            }
        data["interests"] = convert_node_list(data["interests"])
        data["institutes"] = convert_node_list(data["institutes"])
        data["faculties"] = convert_node_list(data["faculties"])
        data["departments"] = convert_node_list(data["departments"])
        data["roles"] = convert_node_list(data["roles"])
        data["offered"] = convert_node_list(data["offered"])
        data["wanted"] = convert_node_list(data["wanted"])
        data["advisors"] = [{
            "name": adv.get("name"),
            "title": adv.get("title"),
            "pk": adv.get("pk"),
            }
            for adv in data["advisors"]]
        entries.append(data)
    return entries

def get_filtered_data(search_param: str) -> list[dict]:
    if search_param == "":
        matching_persons = Person.nodes.all()
    else:
        # this doesn't search email or title of persons
        # "NOT n:Person" prevents searching persons that are advisors to p:Person because
        # there is no point in showing them in the table if a search parameter is given
        query = ("MATCH (p:Person)-[r]-(n) "
                "WHERE toLower(n.name) CONTAINS $search "
                "AND NOT n:Person "
                "OR toLower(p.name) CONTAINS $search "
                "RETURN DISTINCT p;")
        results, _ = db.cypher_query(query, {"search": search_param}, resolve_objects=True)
        matching_persons = [row[0] for row in results]
    return get_all_person_data(matching_persons)

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
    nodes, rels = person.graph_data()
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
    persons_data = get_filtered_data(search_param.lower())
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
