import re
from collections.abc import Iterable
from enum import Enum

from spacy import Language
from spacy.tokens import Doc

from classes.person import Person

class SourceRows(Enum):
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
    _persons: list[Person]

    def __init__(self, nlp: Language) -> None:
        self._nlp = nlp
        self._persons = []
        # is there a better type than lists? like dicts or sets
        # after adding all entries the lists must not be changed (appended, removed)
        self._interests = []
        self._institutes = []
        self._faculties = []
        self._departments = []
        self._advisors = []
        self._roles = []
        self._expertise = []

    def __str__(self) -> str:
        output = []
        for person in self._persons:
            entry = str(person)
            entry += (
                f"\ninterests {self._interests} institutes {self._institutes}"
                f" faculties {self._faculties} departments {self._departments}"
                f" advisors {self._advisors} roles {self._roles}"
                f" expertise {self._expertise}")
            output.append(entry)
        return "\n\n".join(output)

    def add_entry(self, row: list[str]) -> None:
        """takes a table row and adds new Person entry and respective values to the lists"""
        # for every entry check if empty/"--"
        title, name = self._split_title(row[SourceRows.NAME.value])
        email = row[SourceRows.EMAIL.value]
        #email_rating = 0
        if email:
            email_token = self._nlp(email)[0]
            #if email_token.like_email:
            #    email_rating = 1

        comment = row[SourceRows.COMMENT.value]
        person = Person(title, name, email, comment)

        # process the other columns
        # TODO: maybe simply pass the target list here?
        interests_indices = self._get_docs_indices(row, SourceRows.INTEREST, (",", ";"))
        person.interests_extend(interests_indices)

        self._persons.append(person)

    @staticmethod
    def _split_title(name_field: str) -> tuple[str, str]:
        """
        Split a name entry into academic title and name parts
        """
        title_tokens = ("dr.", "prof.", "nat.", ...)
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
        """returns true if string is empty or only hyphens"""
        return value.replace("-", "") == ""

    @staticmethod
    def _get_regex_pattern(delimiters: Iterable[str]):
        return "|".join(map(re.escape, delimiters))

    def _get_docs_indices(self, row: list[str], source_column: SourceRows, delimiters: Iterable[str]) -> list[Doc]:
        entries = row[source_column.value]
        if not self._is_empty(entries):
            indices = []
            split_entries = re.split(self._get_regex_pattern(delimiters), entries)
            docs = [self._nlp(x.strip()) for x in split_entries]

        match source_column:
            case SourceRows.INTEREST:
                target_list = self._interests
            case SourceRows.INSTITUTE:
                target_list = self._institutes
                # TODO: somehow handle faculties and departments
            case SourceRows.ADVISOR:
                target_list = self._advisors
            case SourceRows.ROLE:
                target_list = self._roles
            case SourceRows.OFFERED | SourceRows.WANTED:
                target_list = self._expertise
            # case _: maybe throw error?

        for doc in docs:
            target_list.append(doc)
            # save index of the last added element
            indices.append(len(target_list) - 1)

        return indices

    # @staticmethod
    # def _get_docs(value: str, delimiters: list[str]) -> list[Doc]:
    #     # if not empty
    #     # split
    #     # convert to doc
    #     # add docs to lists
    #     pass

    # def _add_field(self, row: list[str], target_column: SourceRows, person: Person) -> None:
    #     docs = self._get_docs(row[target_column.value])
    #     for doc in :
    #         # add

    #     # add references to person
    #     match target_column:
    #         case SourceRows.INTEREST:
    #             target_list = self._

    # methods for merging

    # def export()
    # log which entries couldn't be converted (e.g. missing email)
