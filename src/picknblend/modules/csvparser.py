import logging
import csv
from typing import Generator, Dict, List


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
    with open(filepath, "rb") as bom:
        filebytes = bom.read()
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
