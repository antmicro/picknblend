import csv
import logging
from typing import Optional
import unidecode
import re
import os
import dataclasses
import functools
from typing import Generator, Dict, List


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class RequiredData:
    """Container for storing extracted data of a single row from the BOM.

    Note that this doesn't contain the entire CSV but only the parts
    that are required for picknblend. `csvnames` defines the names
    of the BOM column that the field will be extracted from. Multiple
    values can be provided if the column name can have multiple
    variants in real-world BOM data.

    You can add a default value to a field by specifying it like so:

        field(metadata={..}, default="my_default").

    The default value is applied if none of the specified column names
    exist.
    """

    footprint: str = dataclasses.field(metadata={"csvnames": ["Footprint"]})
    """Name of the footprint"""
    manufacturer: str = dataclasses.field(metadata={"csvnames": ["Manufacturer"]})
    """Manufacturer of the part"""
    mpn: str = dataclasses.field(metadata={"csvnames": ["MPN"]})
    """Manufacturer part number"""


def _load_and_parse_csv(bom_path: str) -> Generator[Dict[str, str], None, None]:
    """Perform raw parsing of the given CSV file.

    Returns a generator producing dictionaries mapping the values
    found on each row to the keys specified in the CSV header.
    """
    with open(bom_path, "rb") as bom:
        filebytes = bom.read()
        as_str: str = ""
        try:
            as_str = filebytes.decode("utf-8")
        except UnicodeDecodeError:
            as_str = filebytes.decode("utf-8", errors="replace")
            logger.warning(
                f"CSV file: {bom_path} is not valid UTF-8! "
                "Problematic characters will be replaced with Unicode Replacement Character (U+FFFD)"
            )

        reader = csv.DictReader(as_str.splitlines(), skipinitialspace=True)
        for row in reader:
            yield row


def _extract_data_from_row(csvrow: Dict[str, str]) -> RequiredData:
    """Extract data required by picknblend from a given BOM row.

    The row is represented as a dictionary, where the key corresponds
    to the column name from the CSV. This function translates many
    possible names for a column to a single field in the output, like so:

        csvrow["Manufacturer"]
        csvrow["MFN"]                 ->    RequiredData.manufacturer
        csvrow["mfg"]
        ...

    You can add more names by adding them to the `csvnames` list of the
    corresponding field in `RequiredData`.
    """
    args = {}
    for field in dataclasses.fields(RequiredData):
        name: str = field.name
        try:
            csvnames: List[str] = field.metadata["csvnames"]
        except Exception:
            continue

        value = None
        for colname in csvnames:
            if colname in csvrow:
                value = csvrow[colname]
                break

        if value is None:
            # Ignore missing column if the field has default value
            if field.default is not dataclasses.MISSING:
                continue
            raise RuntimeError(
                f"Could not find required column '{name}' in BOM CSV file, tried looking for names: {','.join(csvnames)}"
            )

        args[name] = value

    return RequiredData(**args)


def parse_bom(bom_path: str) -> List[RequiredData]:
    """Parse the whole BOM and return a list of data extracted from it.

    Note: We only extract necessary fields from the BOM, this won't contain
    every column from the original CSV. If you want to add a column to be
    extracted, simply add a field to `RequiredData`.
    """
    bom: List[RequiredData] = []

    if bom_path != "":
        for row in _load_and_parse_csv(bom_path):
            bom.append(_extract_data_from_row(row))

    return bom


def parse_markings(bom_path: str) -> Dict[str, str]:
    """Parse markings from the specified BOM file."""
    marking_id_data: Dict[str, str] = {}

    if bom_path != "":
        logger.info("Importing BOM data")

        for row in _load_and_parse_csv(bom_path):
            data = _extract_data_from_row(row)
            marking_id_data[data.footprint] = convert_to_id(f"{data.manufacturer}-{data.mpn}")

    logger.debug("Parsed marking data: %s", marking_id_data)

    return marking_id_data


def convert_to_id(string: str) -> str:
    # optional step, remove accents
    string_2 = unidecode.unidecode(string)
    string_3 = string_2.lower()
    string_4 = re.sub(r"[^a-z0-9]", " ", string_3)
    string_5 = string_4.strip()
    return re.sub(r"\s+", "-", string_5)
