import bpy
import os
import csv
import re
from unidecode import unidecode
from math import radians, ceil
from mathutils import Vector
import logging
import picknblend.modules.legacy_config as legacy_config
import picknblend.modules.legacy_custom_utilities as cu

logger = logging.getLogger(__name__)


def clean_annotations():
    collections_to_remove = []
    for coll in bpy.data.grease_pencils.keys():
        if "Annotations" in coll:
            collections_to_remove.append(coll)
    for coll in collections_to_remove:
        bpy.data.grease_pencils.remove(bpy.data.grease_pencils[coll])


def import_comp(
    pcb,
    footprint,
    lib_path,
    name,
    posx,
    posy,
    side,
    deg,
    models_imported,
    total_thickness,
    sub_model_pos=[0, 0, 0],
    sub_model_rot=[0, 0, 0],
    marking_name="",
):
    if side != "T" and side != "B":
        logger.error("unknown side: " + str(side))
        return
    posz = total_thickness
    obj_name = footprint[-63:]  # clip too long name to last 63 signs
    if obj_name not in models_imported or marking_name != "":
        try:
            bpy.ops.wm.append(
                filename="Collection",
                instance_collections=False,
                directory=lib_path + footprint + ".blend/Collection/",
            )
            bpy.data.libraries.load(lib_path)
            logger.debug(
                f"{name}: Imported {footprint} from {lib_path}"
                + f" at x: {str(posx)} y: {str(posy)} rot: {str(deg)} {str(side)}"
            )
            models_imported.append(obj_name)
        except ImportError:
            logger.warning(name + ": import_comp() failed!")
            return

        clean_annotations()
        bpy.ops.object.transform_apply(
            location=True,
            rotation=True,
            scale=False,
            properties=False,
            isolate_users=False,
        )
        # name temporary object as (clipped) footprint name
        temp_obj = bpy.context.selected_objects[0]
        temp_obj.name = obj_name
        temp_coll = bpy.data.collections.get("Temp")
        cu.link_obj_to_collection(temp_obj, temp_coll)
        # name target object as ref+sym_name
        new_obj = temp_obj.copy()
        new_obj.name = name
    else:
        logger.debug(
            f"{name}: Duplicated already imported model {footprint}"
            + f" at x: {str(posx)} y: {str(posy)} rot: {str(deg)} {str(side)}"
        )
        bpy.ops.object.select_all(action="DESELECT")
        # get temporary object with footprint name
        src_obj = bpy.data.objects[obj_name]
        # name target object as ref+sym_name
        new_obj = src_obj.copy()
        new_obj.name = name

    if "PRIO" in new_obj.keys():
        if new_obj["PRIO"]:
            comps = bpy.data.collections.get("Misc")
        else:
            comps = bpy.data.collections.get("Components")
    else:
        comps = bpy.data.collections.get("Components")

    cu.link_obj_to_collection(new_obj, comps)
    bpy.context.view_layer.objects.active = None
    new_obj.select_set(True)
    bpy.ops.object.make_single_user(type="SELECTED_OBJECTS", object=True, obdata=True)

    if legacy_config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"]:
        try:
            if new_obj["PRIO"] != 0:  # check only sub-models models
                # add translation/rotation of submodel to initial connector's position
                # Apply submodel rotation
                logger.debug(f"Submodel import position: [{sub_model_pos[0]}, {sub_model_pos[1]}, {sub_model_pos[2]}]")
                logger.debug(f"Submodel import rotation: [{sub_model_rot[0]}, {sub_model_rot[1]}, {sub_model_rot[2]}]")
                rotate = Vector(
                    (
                        radians(sub_model_rot[0]),
                        radians(sub_model_rot[1]),
                        radians(sub_model_rot[2]),
                    )
                )

                new_obj.rotation_euler = rotate
                # Apply submodel transformation
                offset = Vector((sub_model_pos[0], sub_model_pos[1], sub_model_pos[2]))
                new_obj.location = offset
        except:
            logger.debug(f"Model {footprint} does not have PRIO custom property")

    bpy.ops.object.transform_apply(
        location=True,
        rotation=True,
        scale=False,
        properties=False,
        isolate_users=False,
    )

    if side == "T":
        new_obj["PCB_Side"] = "T"
        new_obj.location = Vector(
            (
                float(posx),
                float(posy),
                posz,
            )
        )
        new_obj.rotation_euler = Vector((0, 0, radians(float(deg))))

    else:  # side == "B"
        new_obj["PCB_Side"] = "B"
        new_obj.location = Vector(
            (
                -float(posx),
                float(posy),
                posz,
            )
        )
        new_obj.rotation_euler = Vector((radians(180), 0, radians(float(deg))))

    bpy.ops.object.select_all(action="DESELECT")

    new_obj.location += Vector([-pcb.dimensions.x / 2, -pcb.dimensions.y / 2, 0])
    cu.recalc_normals(new_obj)

    # adding submodels for footprints with several 3D models
    if legacy_config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"] and "PRIO" in list(new_obj.keys()):
        logging.debug(f"'{name}' keys: {list(new_obj.keys())}")
        logging.debug(f"PRIO value: {new_obj['PRIO']}")
        if new_obj["PRIO"] != 0:  # check only main models
            return
        sub_param_count = 4  # number of parameters which define sub-model
        main_param_count = 3  # number of parameters which define main model
        substract_params = len(list(new_obj.keys())) - main_param_count  # number of submodels parameters
        if "cycles" in new_obj.keys():
            substract_params -= 1  # omit unknown 'cycles' property not generated by us
        submodel_count = ceil(substract_params / sub_param_count)  # assumed number of submodels
        if submodel_count == 0:  # if no submodels
            return
        logging.debug("Importing sub-models...")
        logging.debug(f"Number of sub-models count: {submodel_count}")
        for j in range(1, submodel_count + 1):
            submodel_original_name = f"{str(j)}_MODEL_NAME"
            # get name of 3D submodel
            if submodel_original_name not in new_obj.keys():
                logging.debug("Missing data about submodels")
                continue
            submodel_footprint = new_obj[submodel_original_name]
            submodel_name = name + f"_{str(j)}_submodel"
            # get translation and rotation of submodel
            submodel_pos = new_obj[f"{str(j)}_{submodel_footprint}_POS"]
            submodel_rotate = new_obj[f"{str(j)}_{submodel_footprint}_ROTATE"]
            for lib in legacy_config.libraries:
                if os.path.exists(lib + submodel_footprint + ".blend"):
                    import_comp(
                        pcb,
                        submodel_footprint,
                        lib,
                        submodel_name,
                        posx,
                        posy,
                        side,
                        deg,
                        models_imported,
                        total_thickness,
                        submodel_pos,
                        submodel_rotate,
                    )
                    break


def process_one_side(
    pcb,
    pnp_file_name,
    model_summary,
    marking_id_data,
    blend_models_list,
    models_imported,
    total_thickness=0,
):
    csv_input = read_pos_csv(legacy_config.fab_path, pnp_file_name)
    for ref, val, pkg, posx, posy, rot, side in csv_input:
        name = ref + ":" + val

        model_summary["total_models"] += 1
        # check if markings used
        ahid = ""
        if legacy_config.bom_path != "":
            if pkg not in marking_id_data:
                logger.warning(f"Footprint {pkg} not found in BOM file. Ignoring marking")
            elif f"{pkg}-{marking_id_data[pkg]}" in blend_models_list:
                ahid = marking_id_data[pkg]
                pkg = f"{pkg}-{marking_id_data[pkg]}"
        ref_prefix = ref.strip("0123456789")
        if not legacy_config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"] and ref_prefix == "A":
            continue
        # check if blend model exists
        if pkg in blend_models_list:
            file_path = blend_models_list[pkg]
            lib = file_path.split(pkg)[0]
            if lib not in model_summary:
                model_summary[lib] = 1
            else:
                model_summary[lib] += 1

            import_comp(
                pcb,
                pkg,
                file_path.split(pkg)[0],
                name,
                posx,
                posy,
                side,
                rot,
                models_imported,
                total_thickness,
                ahid,
            )
        else:
            logger.warning(name + ": " + pkg + ".blend not found in library")
            model_summary["not_found_models"] += 1

    comp_col = bpy.data.collections.get("Components")
    for obj in comp_col.objects:
        if obj.parent is not None:
            continue
        # set components parent to pcb
        obj.select_set(True)
        pcb.select_set(True)
        bpy.context.view_layer.objects.active = pcb  # active obj will be parent
        bpy.ops.object.parent_set(keep_transform=True)
        bpy.ops.object.select_all(action="DESELECT")

    if legacy_config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"]:
        comp_col = bpy.data.collections.get("Misc")
        for obj in comp_col.objects:
            if obj.parent is not None:
                continue
            # set components parent to pcb
            obj.select_set(True)
            pcb.select_set(True)
            bpy.context.view_layer.objects.active = pcb  # active obj will be parent
            bpy.ops.object.parent_set(keep_transform=True)
            bpy.ops.object.select_all(action="DESELECT")
    return model_summary


def convert_to_id(string: str) -> str:
    # optional step, remove accents
    string_2 = unidecode(string)
    string_3 = string_2.lower()
    string_4 = re.sub(r"[^a-z0-9]", " ", string_3)
    string_5 = string_4.strip()
    return re.sub(r"\s+", "-", string_5)


def get_pnp(pnp_csv_mask):
    """pnp_csv_mask is pnp csv name ending phrase"""

    for file in os.listdir(legacy_config.fab_path):
        if file.endswith(pnp_csv_mask):
            return file
    return False


def remove_materials_duplicates():
    logger.debug("Removing materials duplicates")
    # list of (sorted_name,original_name)
    materials_names = sorted([(mat.name.replace(" ", ""), mat.name) for mat in bpy.data.materials])
    original_name = materials_names[0][1]
    for i in range(len(materials_names)):
        name = materials_names[i][1]
        # print(original_name, name)
        if "." not in name:  # original
            original_name = name
            # print("original")
        else:  # duplicate
            # print("duplicate")
            if (original_name + ".") in name:
                original_material = bpy.data.materials[original_name]
                # iterate through all components
                obj_list = list(bpy.data.collections.get("Components").objects)
                obj_list.extend(
                    list(bpy.data.collections.get("Misc").objects)
                    if bpy.data.collections.get("Misc") is not None
                    else []
                )
                for child in obj_list:
                    for slot in child.material_slots:
                        if (slot.material is not None) and (slot.material.name == name):
                            slot.material = original_material  # replace duplicates with originals
                # print("Remove ", name)
                bpy.data.materials.remove(bpy.data.materials[name])


def import_all_components(board_col, total_thickness):

    # import components
    if bpy.data.collections.get("Components"):
        logger.info("Components already imported.")
        return

    logger.info("Importing components.")
    top_pnp = get_pnp("top-pos.csv")
    bot_pnp = get_pnp("bottom-pos.csv")

    main_col = bpy.data.collections.get(legacy_config.PCB_name)
    marking_id_data = dict()
    if legacy_config.bom_path != "":
        # import BOM data
        logger.info("Importing BOM data")
        with open(legacy_config.bom_path, "r") as bom:
            bom_file = list(csv.reader(bom, delimiter=",", quotechar='"'))
        for line in bom_file[1:]:
            marking_id_data[line[3]] = convert_to_id(f"{line[4]}-{line[5]}")

    cu.create_collection("Components", main_col)
    if legacy_config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"]:
        cu.create_collection("Misc", main_col)

    model_summary = {"total_models": 0, "not_found_models": 0}

    # dict with model names and path to them
    blend_models_list = {}
    for lib_path in legacy_config.libraries:
        for file in os.listdir(lib_path):
            file_split = os.path.splitext(file)
            if file_split[1] == ".blend":
                blend_models_list[file_split[0]] = f"{lib_path}{file}"

    # list of blend models imported
    models_imported = []
    cu.create_collection("Temp", main_col)
    # process top components
    if top_pnp:
        model_summary = process_one_side(
            board_col.objects[-1],
            top_pnp,
            model_summary,
            marking_id_data,
            blend_models_list,
            models_imported,
            total_thickness,
        )

    # process bottom components
    if bot_pnp:
        model_summary = process_one_side(
            board_col.objects[0],
            bot_pnp,
            model_summary,
            marking_id_data,
            blend_models_list,
            models_imported,
        )

    cu.remove_collection("Temp")
    remove_materials_duplicates()

    logger.info("Component blender models summary:")
    for key in model_summary:
        logger.info(key + " = " + str(model_summary[key]))

    for collection in bpy.data.collections:
        if "Collection" in collection.name:
            bpy.data.collections.remove(collection)


def read_pos_csv(path, filename):
    with open(path + filename, "r") as csvfile:
        line = csv.reader(csvfile, delimiter=",", quotechar='"')
        input = list(line)
        input.pop(0)  # remove header line
        sides = {"bottom": "B", "top": "T"}
        for i in range(len(input)):  # change side to single letter
            input[i][-1] = sides[input[i][-1]]
        return input
