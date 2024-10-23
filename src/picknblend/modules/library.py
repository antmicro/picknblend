import os
import functools
import logging
import pathlib
from typing import Dict, List
import picknblend.modules.config as config


logger = logging.getLogger(__name__)


@functools.cache
def _find_models() -> Dict[str, str]:
    """Iterate over all libraries and find available models."""

    logger.warning("Discovering available models - this may take a while on large libraries!")

    blend_models_list: dict[str, str] = {}
    directories_to_search = get_library_directories()
    for lib_path in directories_to_search:
        if not os.path.isdir(lib_path):
            logger.info("Model library %s does not exist - skipping", lib_path)
            continue

        found_count = 0
        root_dir = pathlib.Path(lib_path)
        # NOTE: pathlib.Path.glob default behavior of not following symlinks may change in future Python:
        #   - https://discuss.python.org/t/treating-symlinks-consistently-in-pathlib-path-glob/49233
        #   - https://docs.python.org/3.13/library/pathlib.html#comparison-to-the-glob-module
        #   - https://github.com/python/cpython/issues/77609
        # Since Python 3.13, you can pass recurse_symlinks=False to explicitly
        # state the behavior. We DO NOT want to recurse symlink directories to
        # avoid entering loops. Simple file symlinks are fine, however.
        for subpath in root_dir.glob("**/*.blend"):
            filepath = os.path.join(lib_path, subpath)
            filename = os.path.basename(subpath)
            root, ext = os.path.splitext(filename)
            if ext == ".blend":
                if root in blend_models_list:
                    logger.debug(
                        "Ignoring duplicated model: %s from library: %s (already found in %s)",
                        root,
                        lib_path,
                        blend_models_list[root],
                    )
                    continue

                blend_models_list[root] = filepath
                found_count += 1

        logger.info("Found %d models in %s", found_count, lib_path)

    if len(blend_models_list) == 0:
        logger.warning(
            "Could not find any models in the configured library paths! "
            "Make sure you have installed and configured the model library path correctly."
        )
        logger.warning("Tried looking for .blend files in these directories:")
        for dir in directories_to_search:
            logger.warning("- %s", os.path.abspath(os.path.expandvars(dir)))
        logger.warning("picknblend will still run, however no components will be placed!")

    logger.info("Discovering models done - found %d models in total", len(blend_models_list))
    return blend_models_list


def find_library_by_model(modelpath: str) -> str:
    """Find the library to which a given model belongs to.

    Library here means the base directory from our configuration that
    the model is in. For example, given:

        MODEL_LIBRARY_PATHS=/foo/
        modelpath=/foo/bar/baz.blend

    This function will return /foo/.
    """
    file = pathlib.Path(os.path.abspath(modelpath))
    dirs = get_library_directories()
    for d in dirs:
        directory = pathlib.Path(d)
        if file.is_relative_to(directory):
            return d

    raise RuntimeError(f"Could not determine library for model {modelpath}")


def get_library_directories() -> List[str]:
    """Get a list of configured library directories.

    This takes into consideration the current blendcfg.yaml, and the
    MODEL_LIBRARY_PATHS environment variable.
    """
    config_directories = config.blendcfg["SETTINGS"]["MODEL_LIBRARY_PATHS"]

    # Split by ':' and filter out empty entries when a trailing ':' is present
    optional_env_dirs = os.environ.get("MODEL_LIBRARY_PATHS", "")
    optional_env_dirs_list = list(filter(len, optional_env_dirs.split(":")))
    directories_to_search = optional_env_dirs_list + config_directories

    # Expand environment variables from each path (for example: $HOME)
    directories_to_search = [os.path.abspath(os.path.expandvars(lib_path)) for lib_path in directories_to_search]

    return directories_to_search


def get_available_models() -> Dict[str, str]:
    """Get a dictionary of all available Blender models in the currently
    configured libraries.

    Keys of the dictionary represent the name of the .blend file (without extension),
    while values contain the absolute path to the model. Found models are
    cached after the first call to this function, and no further filesystem
    queries are done when this method is called multiple times (i.e, no new models
    will be found).
    """
    return _find_models()
