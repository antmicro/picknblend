"""Module containing custom utilities functions."""

import bpy
import logging
from typing import Any

logger = logging.getLogger(__name__)


def apply_all_transform_obj(obj: bpy.types.Object) -> None:
    """Apply all object transfromations."""
    obj.select_set(True)
    bpy.ops.object.transform_apply()
    obj.select_set(False)


def recalc_normals(obj: bpy.types.Object) -> None:
    """Recalculate normals in object."""
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")


def create_collection(name: str, parent: bpy.types.Collection | None = None) -> Any:
    """Create and link objects to collection."""
    if not bpy.data.collections.get(name):
        newCol = bpy.data.collections.new(name)
        if parent:
            parent.children.link(newCol)
        else:
            bpy.context.scene.collection.children.link(newCol)
    return bpy.data.collections.get(name)


def remove_collection(name: str) -> None:
    """Remove collection."""
    remCol = bpy.data.collections.get(name)
    if remCol is None:
        logger.debug(f"Did not find '{name}' collection to remove. Continue")
        return
    logger.debug(f"Found '{name}' collection. Removing its objects and whole collection.")
    for obj in remCol.objects:
        bpy.data.objects.remove(obj)
    bpy.data.collections.remove(remCol)


def link_obj_to_collection(obj: bpy.types.Object, target_coll: bpy.types.Collection) -> None:
    """Loop through all collections the obj is linked to and unlink it from there, then link to targed collection."""
    for coll in obj.users_collection:  # type: ignore
        coll.objects.unlink(obj)
    target_coll.objects.link(obj)


def parent_collection_to_object(collection_name: str, parent: bpy.types.Object) -> None:
    """Parent all child objects of the given collection to an object."""
    comp_col = bpy.data.collections.get(collection_name)
    for obj in comp_col.objects:
        if obj.parent is not None:
            continue
        # set parent for all child objects
        obj.select_set(True)
        parent.select_set(True)
        bpy.context.view_layer.objects.active = parent  # active obj will be parent
        bpy.ops.object.parent_set(keep_transform=True)
        bpy.ops.object.select_all(action="DESELECT")


def save_pcb_blend(path: str, apply_transforms: bool = False) -> None:
    """Save the current model at the specified path."""
    if apply_transforms:
        for obj in bpy.context.scene.objects:
            apply_all_transform_obj(obj)
    bpy.ops.wm.save_as_mainfile(filepath=path)


def open_blendfile(blendfile: str) -> None:
    """Open a given .blend file.

    Equivalent to file/open in GUI, will overwrite current file!
    """
    logger.info(f"Opening existing file: {blendfile}")
    bpy.ops.wm.open_mainfile(filepath=blendfile)
