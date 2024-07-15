import os
import picknblend.modules.config as config
import logging


logger = logging.getLogger(__name__)


def get_available_models():
    """Get a dictionary of all available Blender models in the currently
    configured libraries.
    """
    blend_models_list = {}

    for lib_path in config.libraries:
        for file in os.listdir(lib_path):
            file_split = os.path.splitext(file)
            if file_split[1] == ".blend":
                blend_models_list[file_split[0]] = f"{lib_path}{file}"

    return blend_models_list
