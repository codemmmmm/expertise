import re
from collections.abc import Iterable
from typing import Any, Union, Sequence
from enum import Enum, auto
from Levenshtein import jaro_winkler

from spacy import Language
from spacy.tokens import Doc
from neomodel import config

from classes.person import Personn
from classes import models

class SourceColumns(Enum):
    """represents the index of the columns in the source document"""
    NAME = 0
    EMAIL = 1
    INTEREST = 2
    INSTITUTE = 3
    ADVISOR = 4
    ROLE = 5
    OFFERED = 6
    WANTED = 7
    COMMENT = 8

class TargetColumns(Enum):
    INTEREST = auto()
    INSTITUTE = auto()
    FACULTY = auto()
    DEPARTMENT = auto()
    ADVISOR = auto()
    ROLE = auto()
    OFFERED_EXPERTISE = auto()
    WANTED_EXPERTISE = auto()

class DataAssignment:  # better name??? mapping?
    """
    for assigning values to persons and merging values among each other
    """
    def __init__(self, nlp: Language) -> None:
        self._nlp = nlp
        self._similarity_score = 0.85
        self._persons: list[Personn] = []
        # after adding all entries the lists must not be changed (elements removed)!!!
        # use list[Doc] when the entries should be compared by semantic similarity
        self._interests: list[Doc] = []
        self._institutes: list[str] = []
        self._faculties: list[str] = []
        self._departments: list[str] = []
        self._advisors: list[tuple[str, str]] = []
        self._roles: list[str] = []
        self._expertise: list[Doc] = []

    def __str__(self) -> str:
        out = (f"\nINTERESTS {self._interests}\nINSTITUTES {self._institutes}\n"
               f"FACULTIES {self._faculties}\nDEPARTMENTS {self._departments}\n"
               f"ADVISORS {self._advisors}\nROLES {self._roles}\n"
               f"EXPERTISE {self._expertise}\n")
        return out

    def print_persons(self) -> None:
        def get_strings(entries: list[Any], indices: list[int]) -> list[str]:
            output = []
            for index in indices:
                output.append(entries[index])
            return output

        for person in self._persons:
            print(person)
            print(get_strings(self._interests, person.interests_ids))
            print(get_strings(self._institutes, person.institutes_ids))
            print(get_strings(self._faculties, person.faculties_ids))
            print(get_strings(self._departments, person.departments_ids))
            # only works after merging
            advisors = [(x.title, x.name) for x in self._persons]
            print(get_strings(advisors, person.advisors_ids))
            print(get_strings(self._roles, person.roles_ids))
            print(get_strings(self._expertise, person.offered_expertise_ids))
            print(get_strings(self._expertise, person.wanted_expertise_ids))
            print("\n")

    def add_entry(self, row: list[str]) -> None:
        """
        takes a table row and adds new Person entry
        and respective values to the lists
        """
        # for every mandatory entry check if empty/"--"
        title, name = self._split_title(row[SourceColumns.NAME.value])
        email = row[SourceColumns.EMAIL.value]
        # email_rating = 0
        # if email:
        #     email_token = self._nlp(email)[0]
        #     if email_token.like_email:
        #         email_rating = 1

        comment = row[SourceColumns.COMMENT.value]
        person = Personn(title, name, email, comment)

        # maybe simply pass the target list?
        interests_indices = self._add_docs(row, SourceColumns.INTEREST, (",", ";"))
        person.interests_ids.extend(interests_indices)

        (institute_indices,
         faculties_indices, departments_indices
         ) = self._add_institute(row, SourceColumns.INSTITUTE, (",", "/"))
        person.institutes_ids.extend(institute_indices)
        person.faculties_ids.extend(faculties_indices)
        person.departments_ids.extend(departments_indices)

        advisor_indices = self._add_basic_value(row, SourceColumns.ADVISOR, (",", "/"))
        person.advisors_ids.extend(advisor_indices)

        role_indices = self._add_basic_value(row, SourceColumns.ROLE, (",", "/"))
        person.roles_ids.extend(role_indices)

        offered_indices = self._add_docs(row, SourceColumns.OFFERED, (","))
        person.offered_expertise_ids.extend(offered_indices)
        wanted_indices = self._add_docs(row, SourceColumns.WANTED, (","))
        person.wanted_expertise_ids.extend(wanted_indices)

        self._persons.append(person)

    def merge(self) -> None:
        self._merge_advisors()
        self._merge_by_name(TargetColumns.INTEREST)
        self._merge_by_name(TargetColumns.INSTITUTE)
        self._merge_by_name(TargetColumns.FACULTY)
        self._merge_by_name(TargetColumns.DEPARTMENT)
        self._merge_by_name(TargetColumns.ROLE)
        self._merge_by_name(TargetColumns.OFFERED_EXPERTISE)
        self._merge_by_name(TargetColumns.WANTED_EXPERTISE)
        # TODO: implement self._merge_by_meaning()

    def _merge_advisors(self) -> None:
        """
        if an advisor has the same name as a person then change the advisor index
        to point to a person entry. else create a new person and point the advisor
        index to that
        """
        for person in self._persons:
            # use only the last name of the person to match
            person_names = [x.name.split()[-1].lower() for x in self._persons]
            for list_index, advisor_index in enumerate(person.advisors_ids):
                advisor = self._advisors[advisor_index]
                try:
                    index_same_person = person_names.index(advisor[1].split()[-1].lower())
                    # TODO: search again but allow a single letter difference
                    # replace reference to an advisor id with a person id
                    person.advisors_ids[list_index] = index_same_person

                    title_from_person_column = self._persons[index_same_person].title
                    title_from_advisor_column = advisor[0]
                    # TODO: maybe compare on len(titles.split()) to see if it
                    # has more title parts listed rather than a longer title
                    if len(title_from_person_column) < len(title_from_advisor_column):
                        self._persons[index_same_person].title = title_from_advisor_column
                except ValueError:
                    new_person = Personn(advisor[0], advisor[1], "", "")
                    self._persons.append(new_person)
                    person.advisors_ids[list_index] = len(self._persons) - 1

    # instead maybe pass a comparison function to _merge_by_name()
    def _is_similar_word(self, word1: str, word2: str) -> bool:
        return jaro_winkler(word1, word2) > self._similarity_score

    def _merge_by_name(self, target: TargetColumns) -> None:
        entries: dict[str, int] = {}
        source_list: Sequence[Union[Doc, str]]
        match target:
            case TargetColumns.INTEREST:
                source_list = self._interests
            case TargetColumns.INSTITUTE:
                source_list = self._institutes
            case TargetColumns.FACULTY:
                source_list = self._faculties
            case TargetColumns.DEPARTMENT:
                source_list = self._departments
            case TargetColumns.ROLE:
                source_list = self._roles
            case TargetColumns.OFFERED_EXPERTISE | TargetColumns.WANTED_EXPERTISE:
                source_list = self._expertise
            case _:
                raise ValueError

        for person in self._persons:
            match target:
                case TargetColumns.INTEREST:
                    assigned_ids = person.interests_ids
                case TargetColumns.INSTITUTE:
                    assigned_ids = person.institutes_ids
                case TargetColumns.FACULTY:
                    assigned_ids = person.faculties_ids
                case TargetColumns.DEPARTMENT:
                    assigned_ids = person.departments_ids
                case TargetColumns.ROLE:
                    assigned_ids = person.roles_ids
                case TargetColumns.OFFERED_EXPERTISE:
                    assigned_ids = person.offered_expertise_ids
                case TargetColumns.WANTED_EXPERTISE:
                    assigned_ids = person.wanted_expertise_ids
                case _:
                    raise ValueError

            # list_index is the index of the value in the person.list
            # source_index is the index of the value in the source_list
            for list_index, source_index in enumerate(assigned_ids):
                value_to_merge = self._get_value_to_merge(source_list[source_index])

                similar_value_found = False
                for key, merged_value in entries.items():
                    if self._is_similar_word(value_to_merge, key):
                        assigned_ids[list_index] = merged_value
                        similar_value_found = True
                        break
                if not similar_value_found:
                    entries[value_to_merge] = source_index

    @staticmethod
    def _get_value_to_merge(value: Union[Doc, str]) -> str:
        """get the string.lower() value"""
        text = value.text if isinstance(value, Doc) else value
        return text.lower()

    @staticmethod
    def _split_title(name_field: str) -> tuple[str, str]:
        """
        Remove all letters after '(' and split a name entry
        into academic titles and name.
        """
        # TODO: add more titles
        title_tokens = ("dr.", "prof.", "nat.", "rer.", )
        title = []
        name = []
        # remove everything after a '('
        name_field = name_field.split(" (", 1)[0]
        tokens = name_field.split()
        for token in tokens:
            if token.lower() in title_tokens:
                title.append(token)
            else:
                # maybe instead add the rest of the tokens to the name and break
                name.append(token)

        return " ".join(title), " ".join(name)

    @staticmethod
    def _is_empty(value: str) -> bool:
        """returns true if string is empty, only whitespace or only hyphens"""
        return (value.replace("-", "") == "") or value.isspace()

    @staticmethod
    def _get_regex_pattern(delimiters: Iterable[str]) -> str:
        return "|".join(map(re.escape, delimiters))

    def _entries_to_docs(self, split_entries: list[str]) -> list[Doc]:
        return [self._nlp(x.strip()) for x in split_entries]

    def _add_institute(
        self,
        row: list[str],
        source_column: SourceColumns,
        delimiters: Iterable[str]
    ) -> tuple[list[int], list[int], list[int]]:
        """
        add institutes, faculties and departments to DataManagement and
        return indices for each
        """
        entries = row[source_column.value]
        indices_institutes = []
        indices_faculties = []
        indices_departments = []
        if not self._is_empty(entries):
            pattern = self._get_regex_pattern(delimiters)
            split_entries = re.split(pattern, entries)
            split_entries = [x.strip() for x in split_entries]

            for entry in split_entries[0:1]:
                self._institutes.append(entry)
                # save index of the last added element
                indices_institutes.append(len(self._institutes) - 1)

            for entry in split_entries[1:2]:
                self._faculties.append(entry)
                # save index of the last added element
                indices_faculties.append(len(self._faculties) - 1)

            for entry in split_entries[2:]:
                self._departments.append(entry)
                # save index of the last added element
                indices_departments.append(len(self._departments) - 1)

        return indices_institutes, indices_faculties, indices_departments

    def _add_basic_value(self, row: list[str], source_column: SourceColumns, delimiters: Iterable[str]) -> list[int]:
        """
        add entries to DataManagement and
        return indices
        """
        entries = row[source_column.value]
        indices = []
        target_list: list[Any]
        if not self._is_empty(entries):
            pattern = self._get_regex_pattern(delimiters)
            split_entries = re.split(pattern, entries)
            split_entries = [x.strip() for x in split_entries]

            match source_column:
                case SourceColumns.ADVISOR:
                    split_entries = [self._split_title(x) for x in split_entries]
                    target_list = self._advisors
                case SourceColumns.ROLE:
                    target_list = self._roles
                case _: raise ValueError

            for entry in split_entries:
                target_list.append(entry)
                # save index of the last added element
                indices.append(len(target_list) - 1)

        return indices

    def _add_docs(self, row: list[str], source_column: SourceColumns, delimiters: Iterable[str]) -> list[int]:
        """
        add Docs for interests and expertises to DataManagement and
        return indices for each
        """
        entries = row[source_column.value]
        indices = []
        if not self._is_empty(entries):
            pattern = self._get_regex_pattern(delimiters)
            split_entries = re.split(pattern, entries)
            docs = self._entries_to_docs(split_entries)

            match source_column:
                case SourceColumns.INTEREST:
                    target_list = self._interests
                case SourceColumns.OFFERED | SourceColumns.WANTED:
                    target_list = self._expertise
                case _: raise ValueError

            for doc in docs:
                target_list.append(doc)
                # save index of the last added element
                indices.append(len(target_list) - 1)

        return indices

    def _connect_nodes(
        self,
        person_node: models.Person,
        target: TargetColumns,
        values: Sequence[Union[Doc, str, Personn]],
        indices: list[int],
    ) -> None:
        for index in indices:
            any_value = values[index]
            value = any_value.text if isinstance(any_value, Doc) else any_value

            match target:
                case TargetColumns.INTEREST:
                    target_node = (
                        models.ResearchInterest.nodes.get_or_none(name=value)
                        or models.ResearchInterest(name=value).save())
                    person_node.interests.connect(target_node)
                case TargetColumns.INSTITUTE:
                    target_node = (
                        models.Institute.nodes.get_or_none(name=value)
                        or models.Institute(name=value).save())
                    person_node.institutes.connect(target_node)
                case TargetColumns.FACULTY:
                    target_node = (
                        models.Faculty.nodes.get_or_none(name=value)
                        or models.Faculty(name=value).save())
                    person_node.faculties.connect(target_node)
                case TargetColumns.DEPARTMENT:
                    target_node = (
                        models.Department.nodes.get_or_none(name=value)
                        or models.Department(name=value).save())
                    person_node.departments.connect(target_node)
                case TargetColumns.ADVISOR:
                    # TODO: maybe also check for same email?
                    # if models.Person.nodes.get_or_none(name=value.name):
                    #     print(f"advisor {value} of {person_node.name} found")
                    # else:
                    #     print(f"advisor {value} of {person_node.name} not found")
                    target_node = (
                        models.Person.nodes.get_or_none(name=value.name)
                        or models.Person(name=value.name).save())
                    print(target_node)
                    person_node.advisors.connect(target_node)
                case TargetColumns.ROLE:
                    target_node = (
                        models.Role.nodes.get_or_none(name=value)
                        or models.Role(name=value).save())
                    person_node.roles.connect(target_node)
                case TargetColumns.OFFERED_EXPERTISE:
                    target_node = (
                        models.Expertise.nodes.get_or_none(name=value)
                        or models.Expertise(name=value).save())
                    person_node.offered_expertise.connect(target_node)
                case TargetColumns.WANTED_EXPERTISE:
                    target_node = (
                        models.Expertise.nodes.get_or_none(name=value)
                        or models.Expertise(name=value).save())
                    person_node.wanted_expertise.connect(target_node)
                case _:
                    raise ValueError

    def export(self, neo4j_url: str) -> None:
        config.DATABASE_URL = neo4j_url
        for person in self._persons:
            print(person.name)
            person_node = models.Person.nodes.get_or_none(name=person.name)
            # if that person's node was already created (from advisors)
            if person_node:
                person_node.title = person.title
                person_node.comment = person.comment
                if person.email:
                    person_node.email = person.email
            else:
                person_node = models.Person(name=person.name, title=person.title, email=person.email or None, comment=person.comment)
            person_node.save()

            self._connect_nodes(person_node, TargetColumns.INTEREST, self._interests, person.interests_ids)
            self._connect_nodes(person_node, TargetColumns.INSTITUTE, self._institutes, person.institutes_ids)
            self._connect_nodes(person_node, TargetColumns.FACULTY, self._faculties, person.faculties_ids)
            self._connect_nodes(person_node, TargetColumns.DEPARTMENT, self._departments, person.departments_ids)
            # here self._persons must be used instead of self._advisors because the
            # advisors list isn't used anymore after merging advisors/persons
            self._connect_nodes(person_node, TargetColumns.ADVISOR, self._persons, person.advisors_ids)
            self._connect_nodes(person_node, TargetColumns.ROLE, self._roles, person.roles_ids)
            self._connect_nodes(person_node, TargetColumns.OFFERED_EXPERTISE, self._expertise, person.offered_expertise_ids)
            self._connect_nodes(person_node, TargetColumns.WANTED_EXPERTISE, self._expertise, person.wanted_expertise_ids)

