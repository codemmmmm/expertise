from typing import Any, Sequence

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.db.models import Q
from django.db import IntegrityError, DatabaseError
from neomodel import db, NeomodelException, RelationshipTo
from django_neomodel import DjangoNode

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

class ErrorDict(dict):
    """similar to format of django form errors"""
    def __init__(self):
        super().__init__()

    def add_error(self, field: str | None, error: str, full_exception: str | None = None):
        error = {
            "message": error,
            "exception": full_exception,
        }

        if field == None:
            field = "__all__" # form error
        if field in self:
            self[field].append(error)
        else:
            self[field] = [error]

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

def convert_node_list(nodes) -> list[dict[str, DjangoNode]]:
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

def get_graph_data(node_id: str) -> dict:
    nodes, rels = query_graph_data(node_id)
    graph_data = {}
    graph_data["nodes"] = format_nodes_for_graph(nodes)
    graph_data["relationships"] = format_rels_for_graph(rels)
    return graph_data

def query_graph_data(node_id: str) -> tuple[set[Any], list[Any]] :
    query = "MATCH (n1)-[r*1]-(n2) WHERE n1.pk=$id RETURN n1, r, n2"
    results, _ = db.cypher_query(query, {"id": node_id})
    nodes = set()
    rels = []
    if results:
        # add the origin node
        nodes.add(results[0][0])
    for row in results:
        # last relationship in the path/traversal
        rel = row[1][-1]
        rels.append(rel)
        nodes.add(row[2])
    return nodes, rels

def connect_and_disconnect(
        nodes_before_change: Sequence[DjangoNode],
        form_data: Sequence[str],
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
        node = node_class.nodes.get_or_none(pk=key_or_value) or node_class.nodes.get_or_none(name=key_or_value)
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

def change_connected(person: Person, form_data: dict[str, Sequence[str]]) -> None:
    # TODO: catch errors in case node with same name already exists
    # should only happen if the form wasn't sent from the GUI
    # or there was an error loading the initial data into the form
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

def try_update_or_create_person(person: Person, data: dict[str, str | Sequence[str]]) -> Person:
    if not person:
        person = Person()
    person.name = data["name"]
    person.email = data["email"]
    person.title = data["title"]
    person.save()
    return person

def is_same_string_or_list(data1: str | Sequence[str], data2: str | Sequence[str]) -> bool:
    """
    Args:
        data1 (str | Sequence[str]): should not be a list with duplicates
        data2 (str | Sequence[str]): should not be a list with duplicates
    """
    if isinstance(data1, str):
        return data1 == data2
    return set(data1) == set(data2)

def is_same_data(data: dict[str, str | Sequence[str]], old_data: dict[str, str | Sequence[str]]) -> bool:
    """return true if all entries in the dictionaries that have truthy values are equal"""
    for key, value in data.items():
        old_value = old_data[key]
        if not is_same_string_or_list(value, old_value):
            return False
    return True

def get_submission_or_none(person: Person) -> EditSubmission | None:
    """return a submission object if a submission with the person's pk or the person's email and name exists.

    the email(new) is checked for the case that the person doesn't exist in Neo4j yet

    Args:
        person (Person): the person's email can be the same as a submission's email but not the
                            same as an existing person's email
    """
    return EditSubmission.objects.filter(
        Q(person_id=person.pk) |
        Q(person_email_new=person.email) & Q(person_name_new=person.name)
        ).first()

def save_submission(person: Person, data: dict[str, str | Sequence[str]]) -> None:
    """save the submission to the relational database for later approval

    Args:
        person (Person): a Person object that might or might not be saved
        data (dict[str, Sequence[str]]): form data
    """
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
    submission = get_submission_or_none(person) or EditSubmission()
    # if the person existed before this submission
    if Person.nodes.get_or_none(pk=person.pk):
        submission.person_id = person.pk
        submission.person_id_new = person.pk

        old_data = get_person_data(person)
        if is_same_data(data, old_data):
            # if a submission was changed again in a way that there is no difference between
            # the old data and the submission's data, the submission is deleted and not
            # just not submitted

            # instead do "if not submisson.id"?
            submission.save()
            submission.delete()
            return
        for property_name, key in property_and_key_names:
            field_data = old_data[key]
            setattr(submission, property_name, field_data)

    for property_name, key in property_and_key_names:
        field_data = data[key]
        setattr(submission, property_name + "_new", field_data)

    if not submission.person_email:
        submission.person_email = ""
    submission.save()

def get_person_data(person: Person) -> dict[str, str | Sequence[str]]:
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

def get_submissions_forms(submissions: Sequence[EditSubmission]) -> Sequence[dict[str, Any]]:
    """returns forms with the old and new data respectively"""
    data = []
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
    # TODO: in frontend? for the entities that don't have a select option: add new one?
    for submission in submissions:
        old_data = {}
        new_data = {}
        for property_name, key in property_and_key_names:
            old_data[key] = getattr(submission, property_name)
            new_data[key] = getattr(submission, property_name + "_new")

        old_form = EditForm(initial=old_data, prefix=str(submission.id) + "old")
        for field in old_form:
            field.field.disabled = True
        new_form = EditForm(initial=new_data, prefix=str(submission.id) + "new")

        submission_data = {
            "data": list(zip(new_form, old_form)), # order of new, old is important
            "id": submission.id,
        }
        # set attribute for marking changed data
        for new_field, old_field in submission_data["data"]:
            if not is_same_string_or_list(new_field.initial, old_field.initial):
                new_field.new_value_is_different = True
        data.append(submission_data)

    return data

def apply_submission(submission: EditSubmission, data: dict[str, str | Sequence[str]]) -> None:
    db.begin()
    try:
        person_id = submission.person_id
        person = Person.nodes.get_or_none(pk=person_id)
        if not person:
            person = Person()
        person.name = data["name"]
        person.email = data["email"]
        person.title = data["title"]
        person.save()
        change_connected(person, data)
        submission.delete()
    except Exception as e:
        db.rollback()
        raise
    db.commit()

    # TODO: log change

def add_form_error(errors: dict[str, list[dict]], field_name: str, message: str, code=None) -> None:
    """same as django form error format

    Args:
        errors (dict):
        field_name (str): "form" for a form error, else the field name
        message (str):
        code (_type_, optional):
    """

    # TODO: use form.add_form_error instead of this function
    error = {
        "message": message,
        "code": code or "",
    }

    if field_name == "form":
        field_name = "__all__"
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
        person_id = request.POST.get("personId")
        form = EditForm(request.POST)
        if not form.is_valid():
            return HttpResponse(form.errors.as_json(), content_type="application/json", status=422)

        data = form.cleaned_data
        person = Person.nodes.get_or_none(pk=person_id)
        if not person and person_id:
            # means that someone manipulated the hidden value or the person was somehow deleted
            add_form_error(errors, "form", "Sorry, the selected person was not found. Please reload the page.")
            return JsonResponse(errors, status=400)

        db.begin()
        # if the exception cause is properly detected for error messages then the two try blocks can be merged
        try:
            person = try_update_or_create_person(person, data)
        except NeomodelException:
            # TODO: also properly handle error for too long properties
            # e.g. if the form field allows more than database constraint
            db.rollback()
            add_form_error(errors, "email", "This email is already in use.")
            return JsonResponse(errors, status=422)
        try:
            change_connected(person, data)
        except NeomodelException as e:
            db.rollback()
            # TODO: proper error message
            add_form_error(errors, "form", "An entity's name is too long.")
            return JsonResponse(errors, status=422)

        # rollback and write to submission database
        db.rollback()
        try:
            person.refresh()
        except Person.DoesNotExist:
            pass

        try:
            save_submission(person, data)
        except IntegrityError as e:
            message = str(e).lower()
            # should two same emails be accepted for submissions?
            if "unique" in message and "email" in message:
                add_form_error(errors, "email", "This email is already in use")
            else:
                add_form_error(errors, "form", "Sorry, some of the data you entered is invalid")
        except DatabaseError:
            add_form_error(errors, "form", "Sorry, some of the data you entered is invalid")
        if errors:
            return JsonResponse(errors, status=422)

        return JsonResponse({})
    else:
        person = Person.nodes.get_or_none(pk=request.GET.get("id"))
        initial_data = get_person_data(person) if person else {}
        form = EditForm(initial=initial_data)
    context = {
        "nav_edit": get_nav_active_marker(),
        "form": form,
        "person_pk": person.pk if person else "",
    }
    return render(request, "expertise/edit-form.html", context)

def approve(request):
    if request.method == "POST":
        action = request.POST.get("action")
        submission_id = request.POST.get("submissionId")
        errors = ErrorDict()
        if not action or not submission_id or action not in ("approve", "reject"):
            errors.add_error(None, "Sorry, something went wrong. Please reload the page.")
            return JsonResponse(errors, status=400)

        submission = EditSubmission.objects.get(pk=submission_id)
        if action == "reject":
            if submission:
                submission.delete()
            # TODO: send email to notify the person
            return JsonResponse({})

        # for approve action
        if not submission:
            errors.add_error(None, "Sorry, the requested entry was not found. Please reload the page.")
            return JsonResponse(errors, status=400)
        form = EditForm(request.POST, prefix=submission_id + "new")
        if not form.is_valid():
            return HttpResponse(form.errors.as_json(), content_type="application/json", status=422)
        try:
            apply_submission(submission, form.cleaned_data)
        except Exception:
            errors.add_error(None, str(e))
            return JsonResponse(errors, status=422)

        return JsonResponse({})
    else:
        submissions = EditSubmission.objects.all()
        forms = get_submissions_forms(submissions)

        context = {
            "nav_approve": get_nav_active_marker(),
            "forms": forms,
        }
        return render(request, "expertise/approve.html", context)

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
    node_id = request.GET.get("id")
    if node_id in (None, ""):
        data["error"] = "missing parameter: id"
        return JsonResponse(data, status=400)

    # do I need to give a proper error for the case that a node with the given key doesn't exist?
    data["graph"] = get_graph_data(node_id)
    return JsonResponse(data)
