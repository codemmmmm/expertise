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
        # out = (f"{self._title}|{self._name}, {self._email}, {self._interests_ids},"
        #        f"{self._institutes_ids}, {self._faculties_ids}, {self._departments_ids},"
        #        f"{self._advisors_ids}, {self._roles_ids}, {self._offered_expertise_ids},"
        #        f"{self._wanted_expertise_ids}")
        out = f"{self._name}, {self._email}"
        return out

    def interests_extend(self, indices: Iterable[int]) -> None:
        self._interests_ids.extend(indices)

    def institutes_extend(self, indices: Iterable[int]) -> None:
        self._institutes_ids.extend(indices)

    def faculties_extend(self, indices: Iterable[int]) -> None:
        self._faculties_ids.extend(indices)

    def departments_extend(self, indices: Iterable[int]) -> None:
        self._departments_ids.extend(indices)

    def advisors_extend(self, indices: Iterable[int]) -> None:
        self._advisors_ids.extend(indices)

    def roles_extend(self, indices: Iterable[int]) -> None:
        self._roles_ids.extend(indices)

    def offered_extend(self, indices: Iterable[int]) -> None:
        self._offered_expertise_ids.extend(indices)

    def wanted_extend(self, indices: Iterable[int]) -> None:
        self._wanted_expertise_ids.extend(indices)

