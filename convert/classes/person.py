from collections.abc import Iterable

class Person:
    """
    represents an entry of a person
    most instance variables save the indices of array values in DataAssignment
    """

    def __init__(self, title: str, name: str, email: str, comment: str) -> None:
        self.title = title
        self.name = name
        self.email = email
        self.interests_ids: list[int] = []
        self.institutes_ids: list[int] = []
        self.faculties_ids: list[int] = []
        self.departments_ids: list[int] = []
        self.advisors_ids: list[int] = []
        self.roles_ids: list[int] = []
        self.offered_expertise_ids: list[int] = []
        self.wanted_expertise_ids: list[int] = []
        self.comment = comment
        # self._score with bit flag (enums)?
        # should it rate the value that was in the table row or
        # the value that is assigned after I merge all values?

    def __str__(self) -> str:
        # out = (f"{self.title}|{self.name}, {self.email}, {self.interests_ids},"
        #        f"{self.institutes_ids}, {self.faculties_ids}, {self.departments_ids},"
        #        f"{self.advisors_ids}, {self.roles_ids}, {self.offered_expertise_ids},"
        #        f"{self.wanted_expertise_ids}")
        out = f"{self.name}, {self.email}"
        return out
