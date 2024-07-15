import bpy
import os
import logging


logger = logging.getLogger(__name__)


def load_model(blend: str):
    """Load a component model from the given .blend file.

    Returns the newly created object."""
    if not os.path.exists(blend):
        raise RuntimeError(f"Cannot load .blend file: {blend}, as it does not exist on the filesystem!")

    try:
        bpy.ops.wm.append(
            filename="Collection",
            instance_collections=False,
            directory=f"{blend}/Collection",
        )
        bpy.data.libraries.load(blend)
    except Exception as e:
        logger.error("Failed loading model from %s: %s", blend, str(e))
        raise

    logger.debug(f"Imported model: {blend}")

    clean_annotations()
    bpy.ops.object.transform_apply(
        location=True,
        rotation=True,
        scale=False,
        properties=False,
        isolate_users=False,
    )

    return bpy.context.selected_objects[0]


def clean_annotations():
    """Clean all annotation collections that were created during model import."""
    collections_to_remove = []
    for coll in bpy.data.grease_pencils.keys():
        if "Annotations" in coll:
            collections_to_remove.append(coll)
    for coll in collections_to_remove:
        bpy.data.grease_pencils.remove(bpy.data.grease_pencils[coll])
