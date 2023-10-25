from typing import Any, Sequence
import json
import logging

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, QueryDict
from django.db.models import Q
from django.db import IntegrityError, DatabaseError
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.serializers.json import DjangoJSONEncoder
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
    ShareParameters,
)

from expertise.forms import EditForm

logger = logging.getLogger(__name__)

# this shouldn't be used to trim an error message if it is a custom message
MAX_ERROR_LENGTH = 130

class ErrorDict(dict):
    """similar to format of django form errors"""

    def add_error(self, field: str | None, message: str, full_exception: str | None = None) -> None:
        """
        add error message to dict if SEND_EXCEPTIONS_TO_CLIENTS = True.
        currently message is assumed to be a substring of full_exception, so it wouldn't
        show any error to the client when it is set to False
        """
        send_exceptions = getattr(settings, "SEND_EXCEPTIONS_TO_CLIENTS", False)
        error = {
            "message": message if send_exceptions else "", # change this to ignore the setting if it is a custom message
            "exception": full_exception if send_exceptions else "",
        }

        if field is None:
            field = "__all__" # form error
        if field in self:
            self[field].append(error)
        else:
            self[field] = [error]

def get_advisor_suggestions():
    query = (
        "MATCH (p:Person) "
        "WHERE (p)<-[:ADVISED_BY]-() "
        "RETURN p;"
    )
    results, _ = db.cypher_query(query, resolve_objects=True)
    advisors = [row[0] for row in results]
    return advisors

def get_suggestions() -> dict:
    """returns data of all nodes

    the lists with persons and expertise contain all persons/expertise entries.
    this means that e.g. the offered expertise list can have an entry of an expertise node
    that is only used as wanted expertise.
    only the people that are actually advise someone are returned for advisors.
    """
    expertise_nodes = Expertise.nodes.all()
    suggestions = {
        "persons": {
            "class": "person",
            "group_name": "Persons",
            "options": Person.nodes.all(),
        },
        "interests": {
            "class": "interest",
            "group_name": "Topics of Interest",
            "options": ResearchInterest.nodes.all(),
        },
        "institutes": {
            "class": "institute",
            "group_name": "Institutions",
            "options": Institute.nodes.all(),
        },
        "faculties": {
            "class": "faculty",
            "group_name": "Faculties, Centers",
            "options": Faculty.nodes.all(),
        },
        "departments": {
            "class": "department",
            "group_name": "Departments, Groups",
            "options": Department.nodes.all(),
        },
        "advisors": {
            "class": "person",
            "group_name": "Advisors",
            "options": get_advisor_suggestions(),
        },
        "roles": {
            "class": "role",
            "group_name": "Roles",
            "options": Role.nodes.all(),
        },
        "offered_expertise": {
            "class": "expertise",
            "group_name": "Offered Expertise",
            "options": expertise_nodes,
        },
        "wanted_expertise": {
            "class": "expertise",
            "group_name": "Wanted Expertise",
            "options": expertise_nodes,
        },
    }
    return suggestions

def convert_node_list(nodes) -> list[dict[str, DjangoNode]]:
    return [{"name": node.get("name"), "pk": node.get("pk")} for node in nodes]

def get_surname(name: str) -> str:
    return name.split()[-1]

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

    entries.sort(key=lambda x: get_surname(x["person"]["name"]))
    return entries

def get_filtered_data(search_phrases: list[str]) -> list[dict]:
    search_phrases = [x.lower() for x in search_phrases if x != ""]
    if not search_phrases:
        matching_persons = Person.nodes.all()
    else:
        # this doesn't search properties of persons and advisors because I think it's not useful
        query = (
            "MATCH (p:Person)--(n) "
            "WHERE NOT n:Person "
            "WITH p, COLLECT(n.name) AS names "
            "WHERE ALL(phrase IN $searchPhrases WHERE ANY(name IN names WHERE toLower(name) CONTAINS phrase)) "
            "RETURN DISTINCT p;"
        )
        results, _ = db.cypher_query(query, {"searchPhrases": search_phrases}, resolve_objects=True)
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
    query = (
        "MATCH (n1)-[r*1]-(n2) "
        "WHERE n1.pk=$id "
        "RETURN n1, r, n2"
    )
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

def add_missing_select_options(form: EditForm) -> None:
    """
    creates missing options elements for the select fields. necessary because new select
    options that are entered in the edit form aren't saved in Neo4j yet. without this
    the options would not show up in the form.
    """

    select_field_names = (
        "interests",
        "institutes",
        "faculties",
        "departments",
        "advisors",
        "roles",
        "offered",
        "wanted",
    )
    for field_name in select_field_names:
        selected_items: list[str] = form.initial[field_name]
        choices: list[tuple[str, str]] = form.fields[field_name].choices
        choices_keys = [x[0] for x in choices]
        for item in selected_items:
            if not item in choices_keys:
                choices.append((item, item))

def get_form_couple_header(new_data: dict[str, str | Sequence[str]], old_data: dict[str, str | Sequence[str]]) -> tuple[str, str]:
    """returns a short description of the form couple that is shown to the user for
    the collapsed accordion item

    Returns:
        tuple[str, str]: description for new and old
    """
    new = f'{new_data["name"]}, {new_data["email"]}'
    old = f'{old_data["name"]}, {old_data["email"]}'.strip()
    return new, old

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
        add_missing_select_options(new_form)

        submission_data = {
            "data": list(zip(new_form, old_form)), # order of new, old is important
            "id": submission.id,
            "header": get_form_couple_header(new_data, old_data),
        }
        # set attribute for marking changed data
        for new_field, old_field in submission_data["data"]:
            if not is_same_string_or_list(new_field.initial, old_field.initial):
                new_field.new_value_is_different = True
        data.append(submission_data)

    return data

def trim_error(error: str) -> str:
    # with the .. it can be longer than MAX_ERROR_LENGTH
    return error[:MAX_ERROR_LENGTH] + ".." if len(error) > MAX_ERROR_LENGTH else error

def get_error_response_data(errors: dict[str, Any], field_id: str | None = None) -> dict[str, Any]:
    """
    Returns:
        dict[str, Any]: dict with keys 'id' and 'errors'
    """
    data = {
        "id": field_id,
        "errors": errors,
    }
    return data

def apply_submission(person: Person, submission: EditSubmission, data: dict[str, str | Sequence[str]]) -> None:
    db.begin()
    try:
        if not person:
            person = Person()
        person.name = data["name"]
        person.email = data["email"]
        person.title = data["title"]
        person.save()
        change_connected(person, data)
        submission.delete()
    except Exception:
        db.rollback()
        raise
    db.commit()

def stringify_edit_submission_post(post_data: QueryDict) -> str:
    output = []
    for key, values in post_data.lists():
        # the token probably needs to be kept secret
        if key != "csrfmiddlewaretoken":
            output.append(f"{key}{values}")
    return ", ".join(output)

def get_share_params(share_id: str | None) -> ShareParameters | None:
    if not share_id:
        return None
    try:
        return ShareParameters.objects.get(pk=share_id)
    except ShareParameters.DoesNotExist:
        return None

# VIEWS BELOW

def index(request):
    # TODO: use better names for the share_params variable(s)
    share_id = request.GET.get("share")
    share_params = get_share_params(share_id)
    selected_options = []
    persons_data = []
    search_phrases = []
    graph_node_id = ""
    if share_params:
        share_params = QueryDict(share_params.parameters)
        filters = share_params.getlist("filter")
        if filters:
            selected_options = filters
        search_phrases = share_params.getlist("search", [])
        # should the table be filled if only the graph view is shared?
        persons_data = get_filtered_data(search_phrases)
        graph_node_id = share_params.get("graph-node", "")

    # the table data, select2 "tag" and modal with graph need to be initialized on front end
    context = {
        "suggestions": get_suggestions(),
        "selected_options": selected_options,
        "table_data": json.dumps(persons_data, cls=DjangoJSONEncoder),
        "search": json.dumps(search_phrases),
        "graph_node": graph_node_id,
    }
    return render(request, "expertise/index.html", context)

def edit(request):
    context = {
        "persons": Person.nodes.all(),
    }
    # should I instead load the whole form in a single view and just have it hidden until searched?
    # what are the downsides?

    return render(request, "expertise/edit.html", context)

def edit_form(request):
    errors = ErrorDict()
    if request.method == "POST":
        person_id = request.POST.get("personId")
        form = EditForm(request.POST)
        if not form.is_valid():
            return HttpResponse(form.errors.as_json(), content_type="application/json", status=422)

        data = form.cleaned_data
        person = Person.nodes.get_or_none(pk=person_id)
        if not person and person_id:
            # means that someone manipulated the hidden value or the person was somehow deleted
            errors.add_error(None, "Sorry, the selected person was not found. Please reload the page.")
            return JsonResponse(errors, status=400)

        db.begin()
        # if the exception cause is properly detected for error messages then the two try blocks can be merged
        try:
            person = try_update_or_create_person(person, data)
        except NeomodelException as e:
            # TODO: also properly handle error for too long properties
            # e.g. if the form field allows more than database constraint
            db.rollback()

            errors.add_error("email", trim_error(str(e)), str(e)) # or invalid email?
            return JsonResponse(errors, status=422)
        try:
            change_connected(person, data)
        except NeomodelException as e:
            db.rollback()
            # TODO: proper error message
            errors.add_error(None, trim_error(str(e)), str(e))
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
                errors.add_error("email", "This email is already in use", str(e))
            else:
                errors.add_error(None, trim_error(str(e)), str(e))
        except DatabaseError as e:
            errors.add_error(None, trim_error(str(e)), str(e))
        if errors:
            return JsonResponse(errors, status=422)

        return JsonResponse({})
    else:
        person = Person.nodes.get_or_none(pk=request.GET.get("id"))
        initial_data = get_person_data(person) if person else {}
        form = EditForm(initial=initial_data)
    context = {
        "form": form,
        "person_pk": person.pk if person else "",
    }
    return render(request, "expertise/edit-form.html", context)

@permission_required("expertise.change_editsubmission")
def approve(request):
    if request.method == "POST":
        action = request.POST.get("action")
        submission_id = request.POST.get("submissionId")
        errors = ErrorDict()
        if not action or not submission_id or action not in ("approve", "reject"):
            errors.add_error(None, "Sorry, something went wrong. Please reload the page.")
            return JsonResponse(get_error_response_data(errors, submission_id), status=400)

        submission = EditSubmission.objects.filter(pk=submission_id).first()
        if action == "reject":
            if submission:
                log = (
                    f"REJECTED submission by {request.user}:{request.user.id} "
                    f"with REQUEST data = {stringify_edit_submission_post(request.POST)}"
                )
                logger.info(log)
                submission.delete()
            # TODO: send email to notify the person
            return JsonResponse({ "id": submission_id })

        # for approve action
        if not submission:
            errors.add_error(None, "Sorry, the requested entry was not found. Please reload the page.")
            return JsonResponse(get_error_response_data(errors, submission_id), status=400)
        form = EditForm(request.POST, prefix=submission_id + "new")
        if not form.is_valid():
            return HttpResponse(form.errors.as_json(), content_type="application/json", status=422)
        try:
            person = Person.nodes.get_or_none(pk=submission.person_id)
            if person:
                data_before_change = get_person_data(person)
            else:
                data_before_change = "[person was created by this operation]"
            apply_submission(person, submission, form.cleaned_data)
            log = (
                f"APPROVED submission by {request.user}:{request.user.id} "
                f"with REQUEST data = {stringify_edit_submission_post(request.POST)} "
                f"and PREVIOUS data = {data_before_change}"
            )
            logger.info(log)
        except Exception as e:
            errors.add_error(None, trim_error(str(e)), str(e))
            return JsonResponse(get_error_response_data(errors, submission_id), status=422)

        return JsonResponse({ "id": submission_id })
    else:
        submissions = EditSubmission.objects.all()
        forms = get_submissions_forms(submissions)

        context = {
            "forms": forms,
        }
        return render(request, "expertise/approve.html", context)

def persons_api(request):
    data = {}
    if "search" not in request.GET:
        data["error"] = "missing parameter: search"
        return JsonResponse(data, status=400)

    search_phrases = request.GET.getlist("search")
    persons_data = get_filtered_data(search_phrases)
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

def shorten(request):
    if request.method == "POST":
        data = json.loads(request.body)
        parameters = data.get("parameters")
        # TODO: and len(parameters) <= ShareParameters.parameters.field.max_length ?
        if parameters:
            shortened, was_created = ShareParameters.objects.get_or_create(parameters=parameters)
            if not was_created:
                # trigger automatic update of last_used value
                shortened.save()

            value = { "value": shortened.id }
            return JsonResponse(value)
        else:
            error_message = "The request didn't contain a value"

        error = { "error": error_message }
        return JsonResponse(error, status=400)
    else:
        return HttpResponse(status=405)



