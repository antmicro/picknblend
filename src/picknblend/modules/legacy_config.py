import logging
import sys
from os import getcwd, listdir, path
from os import path as pth
from os import readlink

import picknblend.modules.legacy_fileIO as fio
from xdg.BaseDirectory import load_data_paths  # type: ignore

# This module is used to share variables between modules.
# Variables are only accessible after running init_global() in main function.
# https://stackoverflow.com/questions/13034496/using-global-variables-between-files

logger = logging.getLogger(__name__)


def init_global_paths(arguments):
    global project_path
    global kbe_dir_path
    global blendcfg
    global fab_path
    global mat_library_path
    global model_library_path
    global libraries
    global doc_path
    global pcb_blend_path
    global PCB_name

    project_path = getcwd() + "/"
    kbe_dir_path = pth.dirname(__file__) + "/.."
    fio.check_and_copy_blendcfg(project_path, kbe_dir_path)
    # read blendcfg file
    blendcfg = fio.open_blendcfg(project_path, arguments.config_preset, kbe_dir_path)

    # paths:
    fab_path = project_path + blendcfg["NAMING"]["FAB_DIR"] + "/"
    doc_path = project_path + blendcfg["NAMING"]["BOM_DIR"] + "/"
    model_library_path = next(load_data_paths("antmicro-blender-models"), None)
    if model_library_path is None:
        sys.exit("Blender model library not installed")

    libraries = [model_library_path + "/assets/", model_library_path + "/assets/raw/"]
    mat_library_path = model_library_path + "/lib/materials/pcb_materials.blend"

    project_extension = blendcfg["NAMING"]["PROJECT_EXTENSION"]
    if arguments.blend_path is None:
        PCB_name = fio.read_pcb_name(project_path, project_extension)
        pcb_blend_path = fab_path + PCB_name + ".blend"
    else:
        PCB_name = arguments.blend_path.split("/")[-1].replace(".blend", "")
        pcb_blend_path = pth.abspath(arguments.blend_path)


def init_global_data(skip_fab=False):
    global project_path
    global doc_path
    global fab_path
    global blendcfg
    global bom_path

    if not skip_fab:
        fio.check_fab_dir_exist(fab_path)
        # Read BOM if MARKINGS used
        bom_path = ""
        if blendcfg["EFFECTS"]["SHOW_MARKINGS"]:
            if not pth.exists(doc_path):
                logger.error(f"{doc_path} directory not found. Aborting.")
                sys.exit(1)
            for file in listdir(doc_path):
                if file.endswith("BOM-populated.csv"):
                    bom_path = doc_path + file
                    break
            if not pth.isfile(bom_path):
                logger.error(f"No BOM-populated file found in {doc_path}. Aborting.")
                sys.exit(1)
