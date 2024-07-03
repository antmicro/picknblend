import bpy
import traceback
import sys
import argparse
import logging
import picknblend.modules.legacy_config as legacy_config
import picknblend.modules.legacy_custom_utilities as cu
import picknblend.modules.legacy_fileIO as fio
from picknblend.modules.legacy_importer import import_all_components, get_top_bottom_component_lists
from os import path


logger = logging.getLogger(__name__)


def parse_args():
    formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=35)
    parser = argparse.ArgumentParser(
        prog="kbe",
        prefix_chars="-",
        formatter_class=formatter,
        description="kbe - script used to provide PCB 3D models and renders from PCB production files. Program must be run in project workdir.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        "-v",
        "--verbose",
        dest="debug",
        action="store_true",
        help="increase verbosity, print more information",
    )
    parser.add_argument(
        "-r",
        "--regenerate-components",
        action="store_true",
        dest="regenerate",
        help="regenerate components in existing .blend",
    )
    parser.add_argument(
        "-b",
        "--blend-path",
        dest="blend_path",
        help="specify path to input/output .blend file",
    )
    parser.add_argument(
        "-c",
        "--config",
        dest="config_preset",
        help="",
        type=str,
        default="default",
    )

    # arguments = sys.argv[sys.argv.index("--") + 1 :]  # omit blender arguments
    return parser.parse_args()


class CustomFormatter(logging.Formatter):
    # use ansi escape styles
    # https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797#colors--graphics-mode
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[33m"  # ;21;5
    red = "\x1b[31m"  # ;21
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"  # clears formating
    format = "[%(asctime)s] (%(levelname)s) %(message)s"
    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        datefmt = "%H:%M:%S"  # "%d.%m.%Y %H:%M:%S"
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt)
        return formatter.format(record)


def set_logging(use_debug):
    root = logging.getLogger()
    level = logging.DEBUG if use_debug else logging.INFO
    root.setLevel(level)
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(CustomFormatter())
    root.addHandler(stdout_handler)


def clear_scene():
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj)
    while len(bpy.context.scene.collection.children) > 0:
        bpy.data.collections.remove(bpy.context.scene.collection.children[0])


def save_pcb_blend(path, apply_transforms=False):
    # bpy.ops.file.pack_all()  # Pack all used external files into this .blend
    if apply_transforms:
        for obj in bpy.context.scene.objects:
            cu.apply_all_transform_obj(obj)
    bpy.ops.wm.save_as_mainfile(filepath=path)


def establish_needed_data(pcb_blend_path, regenerate):
    """
    This should work according to following logic
    - kbe should be always run with blender model path as argument
    - if 'Assembly' collection is found in the data -> follow the old kbe -b flow for assemblies, set isPCB to false, do not request inputs
    - if 'Board' collection is found but no 'Components' -> request inputs: pnp (mandatory), bom (if SHOW_MARKINGS), set isPCB to true
    - if 'Board' and 'Components' collections are found and regenerate flag not set -> do not request inputs, set isPCB to true
    - if 'Board' and 'Components' collections are found and '-r' switch present -> remove old components and add them once again;
        request inputs: pnp (mandatory), bom (if SHOW_MARKINGS), set isPCB to true
    - if 'Component' and 'Pads' are found -> special case when rendering component (behaviour yet to be established)
    """

    if not path.exists(pcb_blend_path):
        logger.error(f"Blender model: {pcb_blend_path} doesn't exist yet, run gerber2blend first.")
        sys.exit(1)

    type_dict = {
        "isAssembly": False,
        "isPCB": False,
        "isComponent": False,
        "hasComponents": False,
        "hasPads": False,
        "unknown": False,
        "skipData": False,
    }

    collection_mapping = {
        "Assembly": "isAssembly",
        "Board": "isPCB",
        "Components": "hasComponents",
        "Component": "isComponent",
        "Pads": "hasPads",
    }

    with bpy.data.libraries.load(pcb_blend_path) as (data_from, data_to):
        # data_to.collections = data_from.collections
        for collection in data_from.collections:
            if collection in collection_mapping:
                type_dict[collection_mapping[collection]] = True

    if (
        (type_dict["hasComponents"] and type_dict["isPCB"] and not regenerate)
        or type_dict["isAssembly"]
        or type_dict["isComponent"]
    ):
        type_dict["skipData"] = True

    if not any(type_dict[key] for key in collection_mapping.values()):
        logger.warning(
            "This file doesn't have any of supported collections ('Board' and 'Components', 'Assembly', 'Component' and 'Pads')"
        )
        logger.warning("It will be processed as unknown type model.")
        type_dict["skipData"] = True
        type_dict["isUnknown"] = True
    return type_dict


def main():
    try:
        args = parse_args()
        set_logging(args.debug)
        clear_scene()

        legacy_config.init_global_paths(args)
        type_dict = establish_needed_data(legacy_config.pcb_blend_path, args.regenerate)

        legacy_config.init_global_data(skip_fab=type_dict["skipData"])
        legacy_config.isPCB = type_dict["isPCB"]
        legacy_config.isComponent = type_dict["isComponent"]
        fio.open_blendfile(legacy_config.pcb_blend_path)

        if type_dict["isPCB"]:  # isPCB and no components
            #    ========== process single board ==========
            # if no components are found on mesh, imports them and then saves the PCB
            logger.info("Recognized PCB model")
            legacy_config.rendered_obj = bpy.data.objects[legacy_config.PCB_name]
            board_col = bpy.data.collections.get("Board")

            if args.regenerate:
                logger.info("Removing 'Components' collection")
                cu.remove_collection("Components")
            import_all_components(board_col, legacy_config.rendered_obj.dimensions.z)

            if not type_dict["skipData"]:
                save_pcb_blend(legacy_config.pcb_blend_path, apply_transforms=True)

            get_top_bottom_component_lists()

        elif type_dict["isComponent"]:
            #    ========== process component with pads ==========
            logger.info("Recognized component with pads")
            component_col = bpy.data.collections.get("Component", None)
            pads_col = bpy.data.collections.get("Pads", None)

            legacy_config.rendered_obj = component_col.objects[0] if component_col else None
            if legacy_config.rendered_obj is None:
                logger.error("Did not find any object under 'Component' collection. Aborting!")
                sys.exit(1)
            logger.info(f"Found component object: {legacy_config.rendered_obj}")

            cu.apply_display_rot(legacy_config.rendered_obj)
            legacy_config.top_components = pads_col.objects if pads_col else []
            legacy_config.bottom_components = pads_col.objects if pads_col else []

        else:
            #    ========== process assembly/unknown file ==========
            if type_dict["isAssembly"]:
                logger.info("Recognized assembly model")
                col = bpy.data.collections.get("Assembly")
            elif type_dict["isUnknown"]:
                # get main collection under Scene Collection
                col = bpy.context.scene.collection.children[0]
            bbox_mesh = cu.get_bbox_linked(col)
            # parent to empty object (pcb_parent)
            bpy.ops.object.select_all(action="DESELECT")
            for obj in col.objects:
                obj.select_set(True)
            cu.link_obj_to_collection(bbox_mesh, col)
            # active obj will be parent
            bpy.context.view_layer.objects.active = bbox_mesh
            bpy.ops.object.parent_set(keep_transform=True)
            bpy.ops.object.select_all(action="DESELECT")
            legacy_config.rendered_obj = bbox_mesh

    except Exception:
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
