import re
from collections.abc import Iterable
from typing import Any
from enum import Enum

from spacy import Language
from spacy.tokens import Doc

from classes.person import Person

class SourceColumns(Enum):
    NAME = 0
    EMAIL = 1
    INTEREST = 2
    INSTITUTE = 3
    ADVISOR = 4
    ROLE = 5
    OFFERED = 6
    WANTED = 7
    COMMENT = 8

class DataAssignment:  # better name??? mapping?
    """
    for assigning values to persons and merging values among each other
    """

    def __init__(self, nlp: Language) -> None:
        self._nlp = nlp
        self._persons: list[Person] = []
        # is there a better type than lists? like dicts or sets
        # after adding all entries the lists must not be changed (appended, removed)

        # use list[Doc] when the entries should be compared by semantic similarity
        # use Optional ?
        self._interests: list[Doc] = []
        self._institutes: list[str] = []
        self._faculties: list[str] = []
        self._departments: list[str] = []
        self._advisors: list[tuple[str, str]] = []
        self._roles: list[str] = []
        self._expertise: list[Doc] = []

    def __str__(self) -> str:
        output = []
        for person in self._persons:
            entry = str(person)
            entry += (
                f"\nINTERESTS {self._interests}\nINSTITUTES {self._institutes}\n"
                f"FACULTIES {self._faculties}\nDEPARTMENTS {self._departments}\n"
                f"ADVISORS {self._advisors}\nROLES {self._roles}\n"
                f"EXPERTISE {self._expertise}\n")
            output.append(entry)
        return "\n\n".join(output)

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
            print(get_strings(self._advisors, person.advisors_ids))
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
        #email_rating = 0
        if email:
            email_token = self._nlp(email)[0]
            #if email_token.like_email:
            #    email_rating = 1

        comment = row[SourceColumns.COMMENT.value]
        person = Person(title, name, email, comment)

        # maybe simply pass the target list?
        interests_indices = self._add_docs(row, SourceColumns.INTEREST, (",", ";"))
        person.interests_ids.extend(interests_indices)

        (institute_indices,
        faculties_indices,departments_indices
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

    def merge(self):
        self._merge_advisors()

    def _merge_advisors(self):
        # advisors should be connected to existing persons (search advisor.name in names)
        # else added as new persons
        pass

    @staticmethod
    def _split_title(name_field: str) -> tuple[str, str]:
        """
        Split a name entry into academic title and name
        """
        # TODO: add more titles
        title_tokens = ("dr.", "prof.", "nat.", "rer.", )
        title = []
        name = []
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
                # case _: maybe throw error?

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
                # case _: maybe throw error?

            for doc in docs:
                target_list.append(doc)
                # save index of the last added element
                indices.append(len(target_list) - 1)

        return indices

    # methods for merging

    # def export()
    # log which entries couldn't be converted (e.g. missing email)
