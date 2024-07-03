import bpy
import bmesh
from mathutils import Vector, kdtree
import logging
from math import radians

logger = logging.getLogger(__name__)


def apply_all_transform_obj(obj):
    obj.select_set(True)
    bpy.ops.object.transform_apply()
    obj.select_set(False)


def recalc_normals(obj):
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.mesh.select_all(action="DESELECT")

    # make sharp edges
    # select edges on board Edges
    bm = bmesh.from_edit_mesh(obj.data)
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            if edge.calc_face_angle() > 1.5:  # angle between faces in radians
                edge.select_set(True)
    bpy.ops.mesh.mark_sharp()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")


def create_collection(name, parent=None):
    if not bpy.data.collections.get(name):
        newCol = bpy.data.collections.new(name)
        if parent:
            parent.children.link(newCol)
        else:
            bpy.context.scene.collection.children.link(newCol)
    return bpy.data.collections.get(name)


def remove_collection(name):
    remCol = bpy.data.collections.get(name)
    if remCol is None:
        logger.debug(f"Did not find '{name}' collection to remove. Continue")
        return
    logger.debug(f"Found '{name}' collection. Removing its objects and whole collection.")
    for obj in remCol.objects:
        bpy.data.objects.remove(obj)
    bpy.data.collections.remove(remCol)


def link_obj_to_collection(obj, target_coll):
    # Loop through all collections the obj is linked to
    for coll in obj.users_collection:
        # Unlink the object
        coll.objects.unlink(obj)
    # Link object to the target collection
    target_coll.objects.link(obj)
