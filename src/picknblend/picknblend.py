import bpy
import traceback
import sys
import argparse
import logging
import picknblend.modules.config as config
import picknblend.modules.custom_utilities as cu
import picknblend.modules.importer as importer
import picknblend.core.log as log
from os import path


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=35)
    parser = argparse.ArgumentParser(
        prog="picknblend",
        prefix_chars="-",
        formatter_class=formatter,
        description="tool for populating PCB models with components based on BOM/PNP data",
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

    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        # Configure logger based on if we're debugging or not
        log.set_logging(args.debug)
        # Initialize global data
        config.init_global(args)

        cu.open_blendfile(config.pcb_blend_path)
        if "Board" not in bpy.data.collections:
            logger.error("Loaded model does not have the required Board collection!")
            return 1
        if config.PCB_name not in bpy.data.objects:
            logger.error("Loaded model does not have a PCB object named %s!", config.PCB_name)
            return 1

        logger.info("Recognized PCB model")
        pcb = bpy.data.objects[config.PCB_name]
        board_col = bpy.data.collections.get("Board")

        if args.regenerate:
            logger.info("Removing 'Components' collection")
            cu.remove_collection("Components")
            misc_col = bpy.data.collections.get("Misc")
            if misc_col is not None:
                cu.remove_collection("Misc")

        importer.import_all_components(board_col, pcb.dimensions.z)
        cu.save_pcb_blend(config.pcb_blend_path, apply_transforms=True)

    except Exception as e:
        logger.error("%s", str(e), exc_info=True)
        return 1

    finally:
        return 0


if __name__ == "__main__":
    exit(main())
