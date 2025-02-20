"""Module for configuring input data."""

import argparse
import os
from os import getcwd, path
from typing import Dict, Any
import picknblend.core.blendcfg as bcfg
import picknblend.core.schema as sch
import picknblend.modules.file_io as fio


blendcfg: Dict[str, Any] = {}
fab_path: str = ""
prj_path: str = ""
doc_path: str = ""
PCB_name: str = ""
pcb_blend_path: str = ""
bom_path: str = ""
pnb_dir_path: str = ""
args: argparse.Namespace


def init_global(arguments: argparse.Namespace) -> int:
    """Process config and initialize global variables used across modules.

    Args:
    ----
        arguments: CLI arguments

    """
    global prj_path
    global blendcfg
    global args
    global pnb_dir_path

    prj_path = getcwd() + "/"
    pnb_dir_path = path.dirname(__file__) + "/.."

    # Handle blendcfg when argument switch is used and end script
    if arguments.reset_config:
        handle_config(overwrite=True)
        return 0
    if arguments.update_config:
        handle_config()
        return 0

    # Handle blendcfg when no argument is passed and proceed with script
    handle_config()

    schema = sch.ConfigurationSchema()
    blendcfgs = bcfg.open_blendcfg(prj_path, arguments.config_preset)
    blendcfg = bcfg.validate_blendcfg(blendcfgs, schema)

    configure_paths(arguments)

    args = arguments
    return 1


def handle_config(overwrite: bool = False) -> None:
    """Determine if config should be copied or merged, applies overwrite mode if enabled in arguments."""
    if not path.exists(path.join(prj_path, bcfg.BLENDCFG_FILENAME)):
        bcfg.copy_blendcfg(prj_path, pnb_dir_path)
    else:
        bcfg.merge_blendcfg(prj_path, pnb_dir_path, overwrite=overwrite)


def configure_paths(arguments: argparse.Namespace) -> None:
    """Configure global paths that will be searched for HW files.

    Args:
    ----
        arguments: CLI arguments

    """
    global fab_path
    global doc_path
    global bom_path
    global pcb_blend_path
    global PCB_name
    global prj_path

    fab_path = prj_path + blendcfg["SETTINGS"]["FAB_DIR"] + "/"
    if not os.path.isdir(fab_path):
        raise RuntimeError(
            f"There is no {blendcfg['SETTINGS']['FAB_DIR']}/ directory in the current working directory! ({prj_path})"
        )

    doc_path = prj_path + blendcfg["SETTINGS"]["BOM_DIR"] + "/"

    # Determine the name of the PCB to use as a name for the .blend
    if arguments.blend_path is None:
        PCB_name = fio.read_pcb_name(prj_path)
        pcb_blend_path = fab_path + PCB_name + ".blend"
    else:
        PCB_name = arguments.blend_path.split("/")[-1].replace(".blend", "")
        pcb_blend_path = path.abspath(arguments.blend_path)

    # Read BOM if MARKINGS used
    bom_path = ""
    if blendcfg["EFFECTS"]["SHOW_MARKINGS"]:
        if not os.path.isdir(doc_path):
            raise RuntimeError(f"Markings enabled, but {doc_path} directory was not found.")

        for file in os.listdir(doc_path):
            if file.endswith("BOM-populated.csv"):
                bom_path = doc_path + file
                break

        if not os.path.isdir(doc_path):
            raise RuntimeError(f"Could not find a BOM file in {doc_path}")
