import bpy
import os
import logging

logger = logging.getLogger(__name__)


def load_model(blend: str) -> bpy.types.Object | None:
    """Load a component model from the given .blend file.

    Returns the newly created object.
    """
    if not os.path.exists(blend):
        raise RuntimeError(f"Cannot load .blend file: {blend}, as it does not exist on the filesystem!")

    check_result = False
    with bpy.data.libraries.load(blend) as (data_from, data_to):
        collections_count = len(data_from.collections)
        match collections_count:
            case collections_count if collections_count > 1:
                logger.warning(f"Model {blend} has too many collections. It will be omitted.")
                check_result = True
            case 0:
                logger.warning(f"Model {blend} has no collections in it. It will be omitted.")
                check_result = True
    if check_result is True:
        return None
    collection_name = data_from.collections[0]
    try:
        bpy.ops.wm.append(
            filename=collection_name,
            instance_collections=False,
            directory=f"{blend}/Collection",
        )
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

    if not bpy.context.selected_objects:
        return None
    return bpy.context.selected_objects[0]


def clean_annotations() -> None:
    """Clean all annotation collections that were created during model import."""
    collections_to_remove = []
    for coll in bpy.data.grease_pencils.keys():
        if "Annotations" in coll:
            collections_to_remove.append(coll)
    for coll in collections_to_remove:
        bpy.data.grease_pencils.remove(bpy.data.grease_pencils[coll])
