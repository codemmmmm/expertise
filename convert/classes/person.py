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
        self._interests_ids: list[int] = []
        self._institutes_ids: list[int] = []
        self._faculties_ids: list[int] = []
        self._departments_ids: list[int] = []
        self._advisors_ids: list[int] = []
        self._roles_ids: list[int] = []
        self._offered_expertise_ids: list[int] = []
        self._wanted_expertise_ids: list[int] = []
        self._comment = comment
        # self._score with bit flag (enums)?
        # should it rate the value that was in the table row or
        # the value that is assigned after I merge all values?

    def __str__(self) -> str:
        return f"{self._title}|{self._name}, {self._email}, {self._interests_ids} ..."

    def interests_extend(self, indices: Iterable) -> None:
        self._interests_ids.extend(indices)

