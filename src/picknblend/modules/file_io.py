from os import listdir
import logging
import os
from typing import Optional
import picknblend.modules.config as config
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PCB_NAME = "unknownpcb"


def read_pcb_name_from_prj(path: str, extension: str) -> str:
    """Try reading the PCB name from a project file at `path` using extension specified in config.

    This function will fail and throw a `RuntimeError` if `path` is
    not a valid project directory.
    """
    files = listdir(path)
    project_file = [f for f in files if f.endswith(extension)]

    if len(project_file) != 1:
        logger.error(f"There should be only one {extension} file in project main directory!")
        logger.error("Found: " + repr(project_file))
        raise RuntimeError(f"Expected single {extension} file in current directory, got %d" % len(project_file))

    name = Path(project_file[0]).stem
    logger.debug("PCB name: %s", name)
    return name


def read_pcb_name(path: str) -> str:
    """Read the PCB name from the current EDA project."""
    extension = config.blendcfg["NAMING"]["PROJECT_EXTENSION"]
    if extension != "":
        try:
            return read_pcb_name_from_prj(path, extension)
        except Exception:
            logger.warning(f"Failed to find {extension} file!")
        # further logic can be added in a similar way as above

    # default case
    logger.warning("Using default value for PCB name")
    return DEFAULT_PCB_NAME


def find_file_in_fab(suffix: str) -> Optional[str]:
    """Find a file in the fab directory that ends with the given suffix."""

    for file in os.listdir(config.fab_path):
        if file.endswith(suffix):
            return file

    return None
