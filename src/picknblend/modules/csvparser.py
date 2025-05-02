import dataclasses
import logging
import csv
from typing import Generator, Dict, List, Type, TypeVar


logger = logging.getLogger(__name__)


def parse(filepath: str) -> Generator[Dict[str, str], None, None]:
    """Parse key/value data from a given CSV file.

    Returns a generator producing dictionaries mapping the values
    found on each row to the keys specified in the CSV header. Usage
    can be as simple as:

        for row in csvparser.parse("path-to.csv"):
            print(row)

    Internally, this uses Python's csv module but additional handling of
    obscure CSV quirks found in real-world data can be added to this method
    to provide unified parsing for PNP/BOM data.
    """
    with open(filepath, "rb") as csv_file:
        filebytes = csv_file.read()
        as_str: str = ""
        try:
            as_str = filebytes.decode("utf-8")
        except UnicodeDecodeError:
            as_str = filebytes.decode("utf-8", errors="replace")
            logger.warning(
                f"CSV file: {filepath} is not valid UTF-8! "
                "Problematic characters will be replaced with Unicode Replacement Character (U+FFFD)"
            )

        reader = csv.DictReader(as_str.splitlines(), skipinitialspace=True)
        for row in reader:
            yield row


T = TypeVar("T")


def extract_data_from_row(csvrow: Dict[str, str], data_type: Type[T], file_type: str, empty_allowed: bool = False) -> T:
    """Extract data required by picknblend from a given CSV file row.

    The row is represented as a dictionary, where the key corresponds
    to the column name from the CSV. This function translates many
    possible names for a column to a single field in the output, like so:

        csvrow["Footprint"]
        csvrow["Package"]                 ->    data_type.footprint
        csvrow["Fp"]
        ...

    You can add more names by adding them to the `csvnames` list of the
    corresponding field in given `data_type` class.
    """
    args = {}
    for field in dataclasses.fields(data_type):  # type:ignore
        name: str = field.name
        try:
            csvnames: List[str] = field.metadata["csvnames"]
        except Exception:
            continue

        value: None | str | float = None
        for colname in csvnames:
            if colname in csvrow:
                value_type = field.type
                if callable(value_type):
                    if value_type is float and csvrow[colname] == "":
                        csvrow[colname] = "0"
                    value = value_type(csvrow[colname])
                else:
                    value = None

        if value is None and not empty_allowed:
            # Ignore missing column if the field has default value
            if field.default is not dataclasses.MISSING:
                continue
            raise RuntimeError(
                f"Could not find required column '{name}' in {file_type} file, tried looking for names: {','.join(csvnames)}"
            )
        args[name] = value
    return data_type(**args)
