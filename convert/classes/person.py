from collections.abc import Iterable

class Person:
    """
    represents an entry of a person
    most instance variables save the indices of array values in DataAssignment
    """

    def __init__(self, title: str, name: str, email: str, comment: str) -> None:
        self._title = title
        self._name = name
        self._email = email
        self._interests_ids = []
        self._institutes_ids = []
        self._faculties_ids = []
        self._departments_ids = []
        self._advisors_ids = []
        self._roles_ids = []
        self._offered_expertise_ids = []
        self._wanted_expertise_ids = []
        self._comment = comment
        # self._score with bit flag (enums)?
        # should it rate the value that was in the table row or
        # the value that is assigned after I merge all values?

    def __str__(self) -> str:
        return f"{self._title}|{self._name}, {self._email}, {self._interests_ids} ..."

    def interests_extend(self, indices: Iterable) -> None:
        self._interests_ids.extend(indices)

