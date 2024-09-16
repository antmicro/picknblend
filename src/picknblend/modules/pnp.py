"""Module responsible for reading and parsing PNP data from CSV files."""

import dataclasses
import os
import logging
from typing import List
import picknblend.modules.csvparser as csvparser

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ComponentData:
    """Container for storing extracted data of a single row from the PNP file.

    Note that this doesn't contain the entire CSV but only the parts
    that are required for picknblend. `csvnames` defines the names
    of the PNP file column that the field will be extracted from. Multiple
    values can be provided if the column name can have multiple
    variants in real-world PNP data.

    You can add a default value to a field by specifying it like so:

        field(metadata={..}, default="my_default").

    The default value is applied if none of the specified column names
    exist.
    """

    reference: str = dataclasses.field(metadata={"csvnames": ["Ref", "Designator"], "type": str})
    """Reference designator of component"""
    value: str = dataclasses.field(metadata={"csvnames": ["Val"], "type": str})
    """Symbol value of component"""
    footprint: str = dataclasses.field(metadata={"csvnames": ["Package", "Footprint"], "type": str})
    """Footprint name of component"""
    pos_x: float = dataclasses.field(metadata={"csvnames": ["PosX"], "type": float})
    """X-axis position of component"""
    pos_y: float = dataclasses.field(metadata={"csvnames": ["PosY"], "type": float})
    """Y-axis position of component"""
    rot: float = dataclasses.field(metadata={"csvnames": ["Rot"], "type": float})
    """Rotation of component"""
    side: str = dataclasses.field(metadata={"csvnames": ["Side"], "type": str})
    """Side of PCB to place the component"""


def parse_pnp(pnp_file_path: str) -> List[ComponentData]:
    """Parse the whole PNP file and return a list of data extracted from it.

    Note: We only extract necessary fields from the PNP, this won't contain
    every column from the original CSV. If you want to add a column to be
    extracted, simply add a field to `RequiredData`.
    """
    pnp: List[ComponentData] = []

    logger.debug(f"Parsing single PNP file: {pnp_file_path}")
    if not os.path.exists(pnp_file_path):
        raise RuntimeError(f"Given PNP file: {pnp_file_path} does not exist!")
    for row in csvparser.parse(pnp_file_path):
        data = csvparser.extract_data_from_row(row, ComponentData)
        pnp.append(data)
    return pnp


def get_pnp_files(fab_path: str) -> List[ComponentData]:
    """Read all PNP files from /fab directory, parse them and collect into single list."""
    pnp_list: List[ComponentData] = []
    pnp_file_suffix = "pos.csv"
    for file in os.listdir(fab_path):
        file = fab_path + file
        logger.debug(f"Read file: {file}")
        if not file.endswith(pnp_file_suffix):
            continue
        data = parse_pnp(file)
        pnp_list.extend(data)

    sides = {"bottom": "B", "top": "T"}
    for comp in pnp_list:
        if comp.side in sides:
            comp.side = sides[comp.side]  # change value of side to single uppercase letter
    return pnp_list
