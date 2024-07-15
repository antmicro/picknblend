import csv
import os


def read_pos_csv(path: str):
    """Parse a PNP file at the given path."""

    if not os.path.exists(path):
        raise RuntimeError(f"Given PNP file: {path} does not exist!")

    with open(path, "r") as csvfile:
        line = csv.reader(csvfile, delimiter=",", quotechar='"')

        input = list(line)
        input.pop(0)  # remove header line
        sides = {"bottom": "B", "top": "T"}

        for i in range(len(input)):  # change side to single letter
            input[i][-1] = sides[input[i][-1]]

        return input
