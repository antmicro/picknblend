"""Module containing custom utilities functions."""

import bpy
import logging
from typing import Any, List

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


def remove_collection(collections: List[str]) -> None:
    """Remove list of collections."""
    for col in collections:
        rem_col = bpy.data.collections.get(col)
        if rem_col is None:
            logger.debug(f"Did not find '{col}' collection to remove. Continue")
            continue
        logger.debug(f"Found '{col}' collection. Removing its objects and whole collection.")
        for obj in rem_col.objects:
            bpy.data.objects.remove(obj)
        bpy.data.collections.remove(rem_col)


def clear_obsolete_data() -> None:
    """Remove obsolete data."""
    clear_unused_meshes()
    clear_unused_materials()
    remove_empty_collections()


def clear_unused_meshes() -> None:
    """Remove unused meshes from file."""
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def clear_unused_materials() -> None:
    """Remove unused materials from file."""
    for mat in bpy.data.materials:
        if mat.users == 0 or mat.name == "Dots Stroke":
            bpy.data.materials.remove(mat)


def remove_empty_collections() -> None:
    """Remove all collections with no children."""
    for col in bpy.data.collections:
        if not col.all_objects:
            bpy.data.collections.remove(col)


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
