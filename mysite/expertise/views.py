from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from neomodel import db, DoesNotExist, UniqueProperty, RelationshipTo
from django_neomodel import DjangoNode

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

def get_graph_data(person: Person) -> dict:
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

def connect_and_disconnect(
        nodes_before_change: list[DjangoNode],
        form_data: list[str],
        node_class: DjangoNode,
        rel: RelationshipTo,
    ) -> None:
    """connect and disconnect to old and new nodes

    Args:
        nodes_before_change (list): the nodes that were connected to the person before the form was submitted
        form_data (list): primary keys of existing nodes or the name of nodes that should be created
        node_class (DjangoNode)
        rel (RelationshipTo)
    """
    # nodes that were entered in the form and already exist in db
    existing_form_nodes = []
    for key_or_value in form_data:
        key_or_value = key_or_value.strip()
        node = node_class.nodes.get_or_none(pk=key_or_value)
        if node:
            existing_form_nodes.append(node)
            # if the node wasn't connected before
            if node not in nodes_before_change:
                rel.connect(node)
        else:
            node = node_class(name=key_or_value).save()
            rel.connect(node)

    for node in nodes_before_change:
        # if node was connected but is not in the form anymore
        if node not in existing_form_nodes:
            rel.disconnect(node)

def change_connected(person: Person, form_data: dict) -> None:
    data_before_change = person.all_connected(inflate=True)
    groups = [
        ("interests", ResearchInterest, person.interests),
        ("institutes", Institute, person.institutes),
        ("faculties", Faculty, person.faculties),
        ("departments", Department, person.departments),
        ("advisors", Person, person.advisors),
        ("roles", Role, person.roles),
        ("offered", Expertise, person.offered_expertise),
        ("wanted", Expertise, person.wanted_expertise),
    ]
    for key, node_class, rel in groups:
        connect_and_disconnect(data_before_change[key], form_data[key], node_class, rel)

def update_or_create_person(person: Person, person_value: str, data: dict):
    if not person:
        person = Person(name=person_value).save()
    person.email = data["email"]
    person.title = data["title"]
    person.save()
    return person

def get_initial_data(person: Person) -> dict:
    connected_data = person.all_connected()
    data = {
        "name": person.name,
        "email": person.email,
        "title": person.title,
        "interests": [node.get("pk") for node in connected_data["interests"]],
        "institutes": [node.get("pk") for node in connected_data["institutes"]],
        "faculties": [node.get("pk") for node in connected_data["faculties"]],
        "departments": [node.get("pk") for node in connected_data["departments"]],
        "advisors": [node.get("pk") for node in connected_data["advisors"]],
        "roles": [node.get("pk") for node in connected_data["roles"]],
        "offered": [node.get("pk") for node in connected_data["offered"]],
        "wanted": [node.get("pk") for node in connected_data["wanted"]],
    }
    return data

def add_form_error(errors: dict, field_name: str, message: str, code=None) -> dict:
    """same as django form error format"""
    # TODO: use form.add_form_error instead of this function
    error = {
        "message": message,
        "code": code or "",
    }
    if field_name in errors:
        errors[field_name].append(error)
    else:
        errors[field_name] = [error]

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
        "persons": Person.nodes.all(),
    }
    # should I instead load the whole form in a single view and just have it hidden until searched?
    # what are the downsides?

    return render(request, "expertise/edit.html", context)

def edit_form(request):
    errors = {}
    if request.method == "POST":
        # either a pk of an existing person or name of new person
        person_value = request.POST.get("person")
        if not person_value:
            add_form_error(errors, "person", "Please choose a person or enter a new name.")
            return JsonResponse(errors, status=400)
        form = EditForm(request.POST)
        # only checks that a valid email was entered
        if form.is_valid():
            data = form.cleaned_data
            person = Person.nodes.get_or_none(pk=person_value)
            db.begin()
            try:
                person = update_or_create_person(person, person_value, data)
            except Exception as e:
                db.rollback()
                #print(e)
                add_form_error(errors, "email", "This email is already in use.")
                return JsonResponse(errors, status=422)
            db.commit()
            change_connected(person, data)
            return JsonResponse(errors)
        else:
            return HttpResponse(form.errors.as_json(), content_type="application/json", status=422)
    else:
        person = Person.nodes.get_or_none(pk=request.GET.get("id"))
        initial_data = get_initial_data(person) if person else {}
        form = EditForm(initial=initial_data)
    context = {
        "nav_edit": get_nav_active_marker(),
        "form": form,
    }
    return render(request, "expertise/edit-form.html", context)

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
