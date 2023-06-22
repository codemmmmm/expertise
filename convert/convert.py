import csv
import os
import sys

import spacy

from classes.data_assignment import DataAssignment

def main() -> int:
    spacy_model_name = "en_core_web_md"
    nlp = spacy.load(spacy_model_name)

    if not len(sys.argv) >= 2:
        sys.exit("Please pass the absolute path of the CSV file as argument.")
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        sys.exit("File ", csv_path, " does not exist or can't be accessed (permissions).")

    data = DataAssignment(nlp)
    print("Reading CSV...")
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=",", quotechar="|")
        # skip first two lines without actual data
        next(csv_reader)
        next(csv_reader)
        for row in csv_reader:
            data.add_entry(row)

    print("Merging data...")
    data.merge()
    print("Exporting to database...")
    data.export(os.environ["NEO4J_BOLT_URL"])
    return 0

if __name__ == "__main__":
    main()
