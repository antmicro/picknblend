import dataclasses
import logging
import unidecode
import re
from typing import Dict
import picknblend.modules.csvparser as csvparser


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class BomData:
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

    footprint: str = dataclasses.field(metadata={"csvnames": ["Footprint", "Package"], "type": str})
    """Name of the footprint"""
    manufacturer: str = dataclasses.field(metadata={"csvnames": ["Manufacturer", "Mfr"], "type": str})
    """Manufacturer of the part"""
    mpn: str = dataclasses.field(metadata={"csvnames": ["MPN"], "type": str})
    """Manufacturer part number"""


def parse_markings(bom_path: str) -> Dict[str, str]:
    """Parse markings from the specified BOM file.

    Note: We only extract necessary fields from the BOM, this won't contain
    every column from the original CSV. If you want to add a column to be
    extracted, simply add a field to `BomData`.
    """
    marking_id_data: Dict[str, str] = {}

    if bom_path != "":
        logger.info("Importing BOM data")

        for row in csvparser.parse(bom_path):
            data = csvparser.extract_data_from_row(row, BomData)
            marking_id_data[data.footprint] = convert_to_id(f"{data.manufacturer}-{data.mpn}")

    logger.debug("Parsed marking data: %s", marking_id_data)

    return marking_id_data


def convert_to_id(string: str) -> str:
    """Convert string data to unified mfr-mpn format."""
    # optional step, remove accents
    string_2 = unidecode.unidecode(string)
    string_3 = string_2.lower()
    string_4 = re.sub(r"[^a-z0-9]", " ", string_3)
    string_5 = string_4.strip()
    return re.sub(r"\s+", "-", string_5)
