import unittest
import re

import spacy

from classes.data_assignment import DataAssignment

class TestStringProcessing(unittest.TestCase):
    def test_empty_field(self):
        self.assertTrue(DataAssignment._is_empty(""))
        self.assertTrue(DataAssignment._is_empty("-"))
        self.assertTrue(DataAssignment._is_empty("---"))
        self.assertTrue(DataAssignment._is_empty("  "))
        self.assertTrue(DataAssignment._is_empty("\n"))
        self.assertFalse(DataAssignment._is_empty("a"))

    def test_assemble_regex_pattern(self):
        self.assertEqual(DataAssignment._get_regex_pattern([",", ";"]), ",|;")
        self.assertEqual(DataAssignment._get_regex_pattern([",", "\\"]), ",|\\\\")
        self.assertEqual(DataAssignment._get_regex_pattern([".", "/"]), "\.|/")
        self.assertEqual(DataAssignment._get_regex_pattern(["&", "/"]), "\&|/")
        self.assertEqual(DataAssignment._get_regex_pattern([r"&", r"/"]), "\&|/")

    def test_name_title(self):
        original = "Dr. rer. nat. vorname-vorname nachname"
        split = DataAssignment._split_title(original)
        expected = ("Dr. rer. nat.", "vorname-vorname nachname")
        self.assertEqual(expected, split)

    def test_name_title_no_title(self):
        original = "vorname-vorname nachname"
        split = DataAssignment._split_title(original)
        expected = ("", "vorname-vorname nachname")
        self.assertEqual(expected, split)

    def test_name_title_no_name(self):
        original = "Dr. rer. nat."
        split = DataAssignment._split_title(original)
        expected = ("Dr. rer. nat.", "")
        self.assertEqual(expected, split)

    def test_name_title_missing_dot(self):
        original = "Dr. rer nat. vorname-vorname nachname"
        split = DataAssignment._split_title(original)
        expected = ("Dr. nat.", "rer vorname-vorname nachname")
        self.assertEqual(expected, split)

class TestDocs(unittest.TestCase):
    def setUp(self):
        spacy_model_name = "en_core_web_md"
        self._nlp = spacy.load(spacy_model_name)
        self._dataAssignment = DataAssignment(self._nlp)

    def test_split_to_docs1(self):
        entries = "data analytics; federated machin\e learning; application support"
        pattern = self._dataAssignment._get_regex_pattern([";",])
        split_entries = re.split(pattern, entries)
        docs_actual = self._dataAssignment._entries_to_docs(split_entries)
        docs_expected = [
            self._nlp("data analytics"),
            self._nlp("federated machin\e learning"),
            self._nlp("application support")]

        for actual, expected in zip(docs_actual, docs_expected):
            self.assertEqual(actual.text, expected.text)

    def test_split_to_docs2(self):
        entries = "ML/DL in engineering; Digital Twin \ other stuff"
        pattern = self._dataAssignment._get_regex_pattern(["/", "&", "\\", ";"])
        split_entries = re.split(pattern, entries)
        docs_actual = self._dataAssignment._entries_to_docs(split_entries)
        docs_expected = [
            self._nlp("ML"),
            self._nlp("DL in engineering"),
            self._nlp("Digital Twin"),
            self._nlp("other stuff")]

        for actual, expected in zip(docs_actual, docs_expected):
            self.assertEqual(actual.text, expected.text)

class TestAddEntries(unittest.TestCase):
    def setUp(self):
        spacy_model_name = "en_core_web_md"
        nlp = spacy.load(spacy_model_name)
        self._dataAssignment = DataAssignment(nlp)

    def test_add_first_entry(self):
        row = [
            "Dr. Heinz-Jan Kunz",
            "email@tu-dresden.de",
            "data analytics, machine learning, simulation & stuff/",
            "TU Dresden / Computer Science / ZIH",
            "Advisor Adv",
            "Researcher, Professor",
            "Public Relations, DevOps",
            "--",
            "comment"]

        data = self._dataAssignment
        data.add_entry(row)
        person = data._persons[0]
        # 1 person was added
        self.assertEqual(len(data._persons), 1)
        self.assertEqual(person.title, "Dr.")
        self.assertEqual(person.name, "Heinz-Jan Kunz")
        self.assertEqual(person.comment, "comment")

        # roles
        self.assertEqual(data._roles[1], "Professor")
        self.assertEqual(person.roles_ids[1], 1)

        # interests
        self.assertEqual(len(data._interests), 3)
        self.assertEqual(data._interests[0].text, "data analytics")
        self.assertEqual(data._interests[1].text, "machine learning")
        self.assertEqual(data._interests[2].text, "simulation & stuff/")

        self.assertEqual(len(person.interests_ids), 3)
        self.assertEqual(person.interests_ids[0], 0)
        self.assertEqual(person.interests_ids[1], 1)
        self.assertEqual(person.interests_ids[2], 2)

        self.assertEqual(data._interests[person.interests_ids[0]].text, "data analytics")
        self.assertEqual(data._interests[person.interests_ids[1]].text, "machine learning")
        self.assertEqual(data._interests[person.interests_ids[2]].text, "simulation & stuff/")

        # departments
        self.assertEqual(len(data._departments), 1)
        self.assertEqual(data._departments[person.departments_ids[0]], "ZIH")

        # offered expertise
        self.assertEqual(len(person.offered_expertise_ids), 2)
        self.assertEqual(person.offered_expertise_ids[0], 0)
        self.assertEqual(person.offered_expertise_ids[1], 1)

        self.assertEqual(data._expertise[person.offered_expertise_ids[0]].text, "Public Relations")
        self.assertEqual(data._expertise[person.offered_expertise_ids[1]].text, "DevOps")

        # for empty wanted expertise field
        self.assertEqual(len(person.wanted_expertise_ids), 0)
        self.assertEqual(len(data._expertise), 2)

        # TODO: test the other lists after implementing

# TODO: tests for addEntry and merging

if __name__ == "__main__":
    unittest.main()
