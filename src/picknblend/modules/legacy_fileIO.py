import json
import logging
import sys
from os import listdir, path, remove
from pathlib import Path
from shutil import copyfile
from subprocess import run
import bpy
import hiyapyco
from xdg.BaseDirectory import load_data_paths

logger = logging.getLogger(__name__)


blendcfg = "kbe_blendcfg.yaml"


def check_fab_dir_exist(fab_path):
    if not path.exists(fab_path):
        logger.error(f"There is no {fab_path} directory at specified path. Aborting")
        sys.exit(1)


def check_and_copy_blendcfg(file_path, kbe_path):
    global blendcfg
    if not path.exists(file_path + blendcfg):
        logger.warning("Config file not found, copying default template")
        copyfile(kbe_path + "/templates/" + blendcfg, file_path + blendcfg)


########################################


def is_color(arg):
    hex_chars = "0123456789ABCDEF"
    return len(arg) == 6 and all([c in hex_chars for c in arg])


def is_color_preset(arg):
    presets = ["White", "Black", "Blue", "Red", "Green"]  # allowed color keywords
    if arg in presets or is_color(arg):
        return 1


def is_transition(arg):
    first = arg[0] == "True"
    if first and len(arg) == 1:
        return False  # missing backgrounds to use
    options = ["All", "Renders"]
    return all([opt in options for opt in arg[1:]])


# parse color
def hex_to_rgba(hex, alpha=True):
    rgb = []
    for i in (0, 2, 4):
        decimal = int(hex[i : i + 2], 16)
        rgb.append(decimal / 255)
    if alpha:
        rgb.append(1)
    return tuple(rgb)


def parse_true_false(arg):
    # change first to bool, rest remains as list of strings
    tmp = arg.replace(",", "").split()
    tmp[0] = True if tmp[0] == "True" else False
    return tmp


def parse_strings(arg):
    tmp = arg.split(",")
    tmp = [text.strip() for text in tmp]
    return tmp


def check_throw_error(cfg, args, expected_type):
    global blendcfg
    missing_config = False
    val = None
    try:
        val = cfg.get(args[0]).get(args[1])
    except:
        missing_config = True

    if val is None or missing_config:
        logger.error(f"[{args[0]}][{args[1]}] not found in {blendcfg}")
        sys.exit(1)

    check_func = lambda x: False
    error_msg = f"[{args[0]}][{args[1]}] is not a {expected_type}"
    match expected_type:
        case "color":
            check_func = is_color
            error_msg = f"[{args[0]}][{args[1]}] is not a color, should be hex color value"
        case "str":
            check_func = lambda x: type(x) is str
        case "bool":
            check_func = lambda x: type(x) is bool
        case "number":
            check_func = lambda x: type(x) is float or type(x) is int
        case "color_preset":
            check_func = lambda x: is_color_preset
            error_msg = f"[{args[0]}][{args[1]}] is not a color, should be hex color value or presets"
        case "transition":
            check_func = is_transition

    if not check_func(val):  # argument doesn't have desired type
        logger.error(error_msg)
        sys.exit(1)


def check_and_parse_blendcfg(cfg):
    cfg["OUTPUT"]["TRANSITIONS"] = parse_true_false(cfg["OUTPUT"]["TRANSITIONS"])

    # check types
    check_throw_error(cfg, ["SETTINGS", "CYCLES_SAMPLES"], "number")
    check_throw_error(cfg, ["SETTINGS", "FPS"], "number")
    check_throw_error(cfg, ["SETTINGS", "WIDTH"], "number")
    check_throw_error(cfg, ["SETTINGS", "HEIGHT"], "number")
    check_throw_error(cfg, ["SETTINGS", "WEBM_WIDTH"], "number")
    check_throw_error(cfg, ["SETTINGS", "WEBM_HEIGHT"], "number")
    check_throw_error(cfg, ["SETTINGS", "THUMBNAIL_WIDTH"], "number")
    check_throw_error(cfg, ["SETTINGS", "THUMBNAIL_HEIGHT"], "number")
    check_throw_error(cfg, ["SETTINGS", "KEEP_PNGS"], "bool")
    check_throw_error(cfg, ["SETTINGS", "SAVE_SCENE"], "bool")
    check_throw_error(cfg, ["SETTINGS", "THUMBNAILS"], "bool")

    check_throw_error(cfg, ["NAMING", "RENDER_DIR"], "str")
    check_throw_error(cfg, ["NAMING", "FAB_DIR"], "str")
    check_throw_error(cfg, ["NAMING", "BOM_DIR"], "str")
    check_throw_error(cfg, ["NAMING", "PROJECT_EXTENSION"], "str")
    # TODO: add interactive checker

    check_throw_error(cfg, ["EFFECTS", "LIGHTS_COLOR"], "color")
    check_throw_error(cfg, ["EFFECTS", "LIGHTS_INTENSITY"], "number")
    check_throw_error(cfg, ["EFFECTS", "DEPTH_OF_FIELD"], "bool")
    check_throw_error(cfg, ["EFFECTS", "SHOW_MECHANICAL"], "bool")
    check_throw_error(cfg, ["EFFECTS", "SHOW_MARKINGS"], "bool")
    check_throw_error(cfg, ["EFFECTS", "BACKGROUND"], "str")

    check_throw_error(cfg, ["OUTPUT", "RENDERS"], "bool")
    check_throw_error(cfg, ["OUTPUT", "STACKUP"], "bool")
    check_throw_error(cfg, ["OUTPUT", "HOTAREAS"], "bool")
    check_throw_error(cfg, ["OUTPUT", "TRANSITIONS"], "transition")
    check_throw_error(cfg, ["OUTPUT", "ANIMATIONS"], "bool")

    check_throw_error(cfg, ["RENDERS", "TOP"], "bool")
    check_throw_error(cfg, ["RENDERS", "BOTTOM"], "bool")
    check_throw_error(cfg, ["RENDERS", "ORTHO"], "bool")
    check_throw_error(cfg, ["RENDERS", "ISO"], "bool")
    check_throw_error(cfg, ["RENDERS", "PERSP"], "bool")
    check_throw_error(cfg, ["RENDERS", "FRONT"], "bool")
    check_throw_error(cfg, ["RENDERS", "LEFT"], "bool")
    check_throw_error(cfg, ["RENDERS", "RIGHT"], "bool")
    check_throw_error(cfg, ["RENDERS", "PHOTO"], "bool")

    check_throw_error(cfg, ["ANIMATION", "CAMERA360"], "bool")
    check_throw_error(cfg, ["ANIMATION", "CAMERA180"], "bool")
    check_throw_error(cfg, ["ANIMATION", "CAMERA_OVAL"], "bool")
    check_throw_error(cfg, ["ANIMATION", "COMP_RAIN"], "bool")
    check_throw_error(cfg, ["ANIMATION", "COMP_PLACE"], "bool")
    check_throw_error(cfg, ["ANIMATION", "STACKUP_EXPLODE"], "bool")
    check_throw_error(cfg, ["ANIMATION", "LED_ON"], "bool")

    # parse non standard types
    cfg["EFFECTS"]["LIGHTS_COLOR"] = hex_to_rgba(cfg["EFFECTS"]["LIGHTS_COLOR"], 0)

    cfg["EFFECTS"]["BACKGROUND"] = parse_strings(cfg["EFFECTS"]["BACKGROUND"])

    # check setting dependencies
    if cfg["ANIMATION"]["STACKUP_EXPLODE"] and not cfg["OUTPUT"]["STACKUP"]:
        cfg["ANIMATION"]["STACKUP_EXPLODE"] = False
        logger.warning(
            "ANIMATION/STACKUP_EXPLODE turned on but globally EFFECT/STACKUP turned off, stackup won't be rendered in this run"
        )

    model_library_path = next(load_data_paths("antmicro-blender-models"), None)
    bg_dict = dict()
    count_input_bgs = 0
    count_failed_bgs = 0
    for bg in cfg["EFFECTS"]["BACKGROUND"]:
        if bg != "Transparent":
            count_input_bgs += 1
            bg_file_path = model_library_path + "/lib/backgrounds/" + bg + ".blend"
            # check existance of background file
            if not path.isfile(bg_file_path):
                logger.warning(f"No background file found in path: {bg_file_path}. It will be omitted.")
                count_failed_bgs += 1
            elif bg not in bg_dict:
                bg_dict[bg] = bg_file_path
        elif bg not in bg_dict:
            # if Transparent in arguments, add it to render options
            bg_dict[bg] = ""
    # if import of all input backgrounds failed, use transparent
    if count_input_bgs and count_input_bgs == count_failed_bgs:
        logger.warning("None of given background files were found. Render on transparent instead.")
        if "Transparent" not in bg_dict:
            bg_dict["Transparent"] = ""
    cfg["EFFECTS"]["BACKGROUND"] = bg_dict
    return cfg


def open_blendcfg(path, config_preset, kbe_path):
    global blendcfg
    template = f"{kbe_path}/templates/{blendcfg}"
    bcfg = f"{path + blendcfg}"
    config = hiyapyco.load([template, bcfg], method=hiyapyco.METHOD_MERGE)
    if config_preset not in config:
        logger.error(f"Unknown blendcfg preset: {config_preset}")
        exit(1)
    return check_and_parse_blendcfg(config[config_preset])


########################################


def read_pcb_name(path, project_extension):
    try:
        files = listdir(path)
        filtered_ext_files = [f for f in files if f.endswith(project_extension)]
        if len(filtered_ext_files) != 1:
            logger.error("There should be only one main project file in current directory!")
            logger.error("Found: " + repr(filtered_ext_files))
            exit(1)
        PCB_name = Path(filtered_ext_files[0]).stem
        logger.debug("PCB_name = " + PCB_name)
    except:
        logger.warning("Failed to find main projet file!")
        exit(1)
    return PCB_name


########################################


# equivalent to file/open in GUI,
# will overwrite current file!
def open_blendfile(blendfile):
    logger.info(f"Opening existing file: {blendfile}")
    bpy.ops.wm.open_mainfile(filepath=blendfile)
