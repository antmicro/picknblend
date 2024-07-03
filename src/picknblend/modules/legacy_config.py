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
    global mat_blend_path
    global model_library_path
    global env_texture_name
    global env_texture_path
    global libraries
    global anim_path
    global doc_path
    global renders_path
    global hotareas_path
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
    renders_path = project_path + blendcfg["NAMING"]["RENDER_DIR"] + "/"
    anim_path = project_path + "assets/previews/"
    hotareas_path = project_path + "assets/hotareas/"
    mat_blend_path = kbe_dir_path + "/templates/materials.blend"
    model_library_path = next(load_data_paths("antmicro-blender-models"), None)
    if model_library_path is None:
        sys.exit("Blender model library not installed")

    libraries = [model_library_path + "/assets/", model_library_path + "/assets/raw/"]
    mat_library_path = model_library_path + "/lib/materials/pcb_materials.blend"

    env_texture_name = "studio_small_03_4k.exr"
    env_texture_path = kbe_dir_path + "/templates/" + env_texture_name
    mat_blend_path = kbe_dir_path + "/templates/materials.blend"

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
    global cam_types
    global all_light_objects
    global top_components
    global bottom_components
    global rendered_obj
    global isPCB
    global isComponent

    rendered_obj = None
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

    # lists automatically appended when light/camera class object made
    all_light_objects = []
    top_components = []
    bottom_components = []

    # type : index for blendcfg COMP_ONLY[]
    cam_types = {
        "ORTHO": 0,
        "ISO": 1,
        "PERSP": 2,
        "FRONT": 3,
        "LEFT": 4,
        "RIGHT": 5,
        "PHOTO": 6,
    }


# blender requirement, usefull for API additions
def register():
    pass


def unregister():
    pass


if __name__ == "__main__":
    register()
