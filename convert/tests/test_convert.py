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
        docs_actual = self._dataAssignment._entries_to_docs(entries, pattern)
        docs_expected = [
            self._nlp("data analytics"),
            self._nlp("federated machin\e learning"),
            self._nlp("application support")]

        for actual, expected in zip(docs_actual, docs_expected):
            self.assertEqual(actual.text, expected.text)

    def test_split_to_docs2(self):
        entries = "ML/DL in engineering; Digital Twin \ other stuff"
        pattern = self._dataAssignment._get_regex_pattern(["/", "&", "\\", ";"])
        docs_actual = self._dataAssignment._entries_to_docs(entries, pattern)
        docs_expected = [
            self._nlp("ML"),
            self._nlp("DL in engineering"),
            self._nlp("Digital Twin"),
            self._nlp("other stuff")]

        for actual, expected in zip(docs_actual, docs_expected):
            self.assertEqual(actual.text, expected.text)


# tests for addEntry and merging

if __name__ == "__main__":
    unittest.main()
