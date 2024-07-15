import csv
import logging
from typing import Optional
import unidecode
import re
import os


logger = logging.getLogger(__name__)


def load_bom(bom_path: str) -> dict:
    """Parse BOM data from the given BOM CSV file.

    The format is to be documented.
    """
    marking_id_data = dict()
    if bom_path != "":
        # import BOM data
        logger.info("Importing BOM data")
        with open(bom_path, "r") as bom:
            bom_file = list(csv.reader(bom, delimiter=",", quotechar='"'))
        for line in bom_file[1:]:
            marking_id_data[line[3]] = convert_to_id(f"{line[4]}-{line[5]}")

    return marking_id_data


def convert_to_id(string: str) -> str:
    # optional step, remove accents
    string_2 = unidecode.unidecode(string)
    string_3 = string_2.lower()
    string_4 = re.sub(r"[^a-z0-9]", " ", string_3)
    string_5 = string_4.strip()
    return re.sub(r"\s+", "-", string_5)
