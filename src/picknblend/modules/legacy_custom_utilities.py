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


def get_parent_object(collection):
    """Get object out of collection that doesn't have any parent - this is the main object that has nested layers inside"""
    for object in collection.objects:
        if not object.parent:
            return object
    return None


# returns list of object's vertices with float precision =-1
def get_vertices(obj, precision=0):
    verts = [vert.co for vert in obj.data.vertices]
    plain_verts = [vert.to_tuple(precision) for vert in verts]
    return plain_verts


def make_kd_tree(verts):
    main_list = list(verts)
    kd = kdtree.KDTree(len(main_list))
    for i, v in enumerate(main_list):
        kd.insert(v, i)
    kd.balance()
    return kd


# remove set of vertices from another set
def get_verts_difference(main_set, remove_set):
    main_list = list(main_set)
    kd = make_kd_tree(main_list)
    indexes_to_remove = []
    for vert in remove_set:
        point, index, dist = kd.find(vert)
        if dist < 0.0001:  # points in the same place
            indexes_to_remove.append(index)

    for id in sorted(indexes_to_remove, reverse=True):
        main_list.pop(id)
    return main_list


# check if there are common vertices for two sets (using previously created kdtree)
def verts_in(kd, add_set):
    for vert in add_set:
        point, index, dist = kd.find(vert)
        if dist:
            if dist < 0.0001:  # points in the same place
                return True
    return False


def get_bbox(obj, arg):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    bbox_vert = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    if arg == "centre":  # finds current center point of the model
        #       centre = sum((Vector(b) for b in obj.bound_box), Vector())
        centre = sum(bbox_vert, Vector())
        centre /= 8
        return centre
    elif arg == "2d":
        corner2d = [corner.to_2d() for corner in bbox_vert]
        return corner2d[::2]
    elif arg == "3d":
        return bbox_vert


# for getting bbox of all linked objects on scene
def get_bbox_linked(collection):
    vertices = []
    edges = []
    faces = []
    collection_objects = [obj.name for obj in collection.objects]
    for obj in bpy.data.objects:
        if obj.type == "LIGHT":
            continue
        if obj.library:  # if object comes from linked library
            lib_name = obj.library.name.replace(".blend", "")
            if lib_name in collection_objects:  # if library is from found collection
                logger.debug(f"Found linked object {obj.name} from {lib_name} lib in {collection.name} Collection")
                lib_obj = bpy.data.objects.get(lib_name)
                bbox = [
                    lib_obj.matrix_world @ Vector(corner) for corner in obj.bound_box
                ]  # applies entire object's source library transformation matrix
                vertices.extend(bbox)
        elif obj.name in collection_objects:  # if object is locally added
            logger.debug(f"Found local object {obj.name} in {collection.name} Collection")
            bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            vertices.extend(bbox)
    if not len(vertices):
        raise (f"{collection.name} collection is empty. Aborting!")
    mesh = bpy.data.meshes.new("assembly_bbox")
    bbox_verts = calculate_bbox(vertices)
    mesh.from_pydata(bbox_verts, edges, faces)
    mesh.update()
    obj = bpy.data.objects.new("assembly_bbox", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# calculates bounding box out of list of Vector(x,y,z)
def calculate_bbox(vector):
    # Initialize min and max values with the coordinates of the first point
    min_x, min_y, min_z = max_x, max_y, max_z = vector[0].x, vector[0].y, vector[0].z

    # Update min and max values by iterating through the list of points
    for point in vector:
        min_x = min(min_x, point.x)
        min_y = min(min_y, point.y)
        min_z = min(min_z, point.z)
        max_x = max(max_x, point.x)
        max_y = max(max_y, point.y)
        max_z = max(max_z, point.z)
    # Construct the 8-point bounding box coordinates
    bounding_box = [
        (min_x, min_y, min_z),
        (min_x, max_y, min_z),
        (max_x, max_y, min_z),
        (max_x, min_y, min_z),
        (min_x, min_y, max_z),
        (min_x, max_y, max_z),
        (max_x, max_y, max_z),
        (max_x, min_y, max_z),
    ]
    return bounding_box


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


def face_sel(obj, pos, edge_verts=[]):
    bpy.context.view_layer.objects.active = obj
    mesh = obj.data
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bm = bmesh.from_edit_mesh(mesh)
    bm.faces.ensure_lookup_table()
    kd = make_kd_tree(edge_verts)
    for face in obj.data.polygons:
        if pos == "edge":
            # check vertical faces
            if abs(face.normal.z) <= 0.5:
                # check if face contains vertices from list
                face_edges = []
                for ind in face.vertices:
                    face_edges.append(obj.data.vertices[ind].co)
                if verts_in(kd, face_edges):
                    bm.faces[face.index].select = True
        elif pos == "top":
            bm.faces[face.index].select = face.normal.z > 0.5
        elif pos == "bot":
            bm.faces[face.index].select = face.normal.z < -0.5
        else:
            logger.error("Specify pos")
    bmesh.update_edit_mesh(mesh)


def face_desel(obj):
    mesh = obj.data
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(mesh)
    bm.faces.ensure_lookup_table()
    for face in obj.data.polygons:
        bm.faces[face.index].select = False


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


def apply_display_rot(obj):
    """Apply rotation based on DISPLAY_ROT property in component model.
    DISPLAY_ROT property can be used to ensure the model appears in upright position on render (usually when looking at the marking).
    """
    logger.debug(f"DISPLAY_ROT value: {obj.get('DISPLAY_ROT')}")
    if display_rot := obj.get("DISPLAY_ROT"):
        logger.info(f"Rotating model using DISPLAY_ROT! ({display_rot}deg)")
        rotation = radians(int(display_rot))
        obj.rotation_euler = [0, 0, rotation]
        bpy.ops.object.transform_apply(
            location=False,
            rotation=True,
            scale=False,
            properties=False,
            isolate_users=False,
        )
