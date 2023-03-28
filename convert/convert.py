import csv

import spacy

from classes.data_assignment import DataAssignment

# read data
# ...
# tokenize with custom tokenizer that may be different for each column
    # or instead re.split() und dann nlp() für jedes item
    # und davor leerzeichen trimmen
    # maybe fully tokenize and then merge until it sees a separation character
    # retokenizer.merge
# save a reference to all tokens of a column that a person has
# merge and process tokens
    # turn similar tokens into one
    # adjust the references people have to it
    # remove the old value so it won't be used again for comparing
    # rate quality of the tokens/column (nothing entered when it should have something)
        # bad values if "-," "- and" ":" "and" "("
    # what to do with abbreviations in braces (ABK)
#

def main() -> int:
    spacy_model_name = "en_core_web_md"
    nlp = spacy.load(spacy_model_name)
    csv_path = "/home/moritz/VirtualBox VMs/competence_matrix.csv"
    data = DataAssignment(nlp)
    i = 0
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        # maybe csv.DictReader instead
        csv_reader = csv.reader(csvfile, delimiter=",", quotechar="|")
        # skip first two lines without actual data
        next(csv_reader)
        next(csv_reader)
        for row in csv_reader:
            # print(", ".join(row))
            if i < 5:
                data.add_entry(row)
                # for s in row:
                #    print(s)
                # print()
            i += 1

    print(data)
    return 0

if __name__ == "__main__":
    main()

# make a function where I merge values from one column
# make a function where I map values from two columns to each other
# (nur für Name, aber für die beiden Expertisespalten sollte ich einfach nur zwei Spalten als eine nutzen?)
