from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
from unidecode import unidecode
from math import radians, ceil
from mathutils import Vector
import bpy
import logging
import os
import picknblend.modules.custom_utilities as cu
import picknblend.modules.config as config
import picknblend.modules.bom as bom
import picknblend.modules.library as library
import picknblend.modules.pnp as pnp
import picknblend.modules.components as components
import picknblend.modules.file_io as fio


logger = logging.getLogger(__name__)


@dataclass
class ImporterData:
    """Contains data that is used by the importer for determining the models to use."""

    # Inputs

    blend_models_list: dict[str, str] = field(default_factory=dict)
    """Mapping of footprint -> blend file name."""
    marking_id_data: dict[str, str] = field(default_factory=dict)
    """BOM data (mapping of footprint -> ID)"""

    # Modified by the importer

    models_imported: list[str] = field(default_factory=list)
    """List of models that were imported (object names)."""
    model_summary: defaultdict = field(default_factory=lambda: defaultdict(int))
    """Summary of imported models per-library."""


def import_all_components(board_col, total_thickness):
    """Import all components from PNP data and put them on the board."""

    if bpy.data.collections.get("Components"):
        logger.info("Components already imported.")
        return
    logger.info("Importing components.")

    importer = ImporterData()
    importer.marking_id_data = bom.parse_markings(config.bom_path)
    importer.blend_models_list = library.get_available_models()

    main_col = bpy.data.collections.get(config.PCB_name)
    cu.create_collection("Components", main_col)
    if config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"]:
        cu.create_collection("Misc", main_col)

    # process top components
    top_pnp = fio.find_file_in_fab("top-pos.csv")
    if top_pnp:
        process_one_side(
            importer,
            board_col.objects[-1],
            top_pnp,
            total_thickness,
        )

    # process bottom components
    bot_pnp = fio.find_file_in_fab("bottom-pos.csv")
    if bot_pnp:
        process_one_side(
            importer,
            board_col.objects[0],
            bot_pnp,
        )

    cu.remove_collection("Temp")
    remove_duplicated_materials()

    logger.info("Component blender models summary:")
    for key in importer.model_summary:
        logger.info(key + " = " + str(importer.model_summary[key]))

    for collection in bpy.data.collections:
        if "Collection" in collection.name:
            bpy.data.collections.remove(collection)


def process_one_side(
    importer: ImporterData,
    pcb,
    pnp_file_name: str,
    total_thickness: float = 0,
):
    """Import components from a given PNP file onto the specified PCB object."""

    csv_input = pnp.read_pos_csv(os.path.join(config.fab_path, pnp_file_name))
    for ref, val, pkg, posx, posy, rot, side in csv_input:
        importer.model_summary["total_models"] += 1

        name = ref + ":" + val
        # check if markings used
        if config.blendcfg["EFFECTS"]["SHOW_MARKINGS"]:
            if pkg not in importer.marking_id_data:
                logger.warning(f"Footprint {pkg} not found in BOM file. Ignoring marking")
            elif f"{pkg}-{importer.marking_id_data[pkg]}" in importer.blend_models_list:
                ahid = importer.marking_id_data[pkg]
                pkg = f"{pkg}-{importer.marking_id_data[pkg]}"

        ref_prefix = ref.strip("0123456789")
        if not config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"] and ref_prefix == "A":
            continue

        # check if blend model exists
        if pkg not in importer.blend_models_list:
            logger.warning(name + ": " + pkg + ".blend not found in library")
            importer.model_summary["not_found_models"] += 1
            continue

        file_path = importer.blend_models_list[pkg]
        lib = library.find_library_by_model(file_path)
        importer.model_summary[lib] += 1

        import_comp(
            importer,
            pcb,
            pkg,
            name,
            posx,
            posy,
            side,
            rot,
            total_thickness,
        )

    cu.parent_collection_to_object("Components", pcb)
    if config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"]:
        cu.parent_collection_to_object("Misc", pcb)


def create_component(importer: ImporterData, footprint: str):
    """Create a component object for the given footprint.

    If no components of this footprint were previously loaded, the model
    is loaded. Otherwise, an existing component model with this footprint
    is cloned.
    """
    obj_name = footprint[-63:]  # clip too long name to last 63 signs
    if obj_name not in importer.models_imported:
        # Component was not loaded yet, attempt to load it
        if footprint not in importer.blend_models_list:
            raise RuntimeError(f"Cannot create component for footprint {footprint}: no model available in library!")
        blendpath = importer.blend_models_list[footprint]
        component = components.load_model(blendpath)

        # Name the component based on shortened footprint name
        # This is used to later be able to duplicate already imported models.
        component.name = obj_name
        temp_coll = cu.create_collection("Temp")
        cu.link_obj_to_collection(component, temp_coll)
        importer.models_imported.append(obj_name)

        logger.debug(f"Imported new model for footprint: {obj_name} and moved to Temp collection")

        # Copy the component - this one will be actually placed on the board
        return component.copy()
    else:
        logger.debug(f"Duplicated already imported model for footprint: {footprint}")
        bpy.ops.object.select_all(action="DESELECT")
        return bpy.data.objects[obj_name].copy()


def import_comp(
    importer: ImporterData,
    pcb,
    footprint: str,
    name: str,
    posx: float,
    posy: float,
    side: str,
    deg: float,
    total_thickness: float,
    sub_model_pos=[0, 0, 0],
    sub_model_rot=[0, 0, 0],
):
    """Import a component onto the PCB.

    Import a single component with `footprint` onto the specified `pcb` object.
    When looking up models for the footprint, mappings from the `importer` class
    are used.
    """
    if side != "T" and side != "B":
        logger.error("unknown side: " + str(side))
        return

    posz = total_thickness
    component = create_component(importer, footprint)
    component.name = name

    if "PRIO" in component.keys():
        if component["PRIO"]:
            comps = bpy.data.collections.get("Misc")
        else:
            comps = bpy.data.collections.get("Components")
    else:
        comps = bpy.data.collections.get("Components")
    cu.link_obj_to_collection(component, comps)

    bpy.context.view_layer.objects.active = None
    component.select_set(True)
    bpy.ops.object.make_single_user(type="SELECTED_OBJECTS", object=True, obdata=True)

    if config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"]:
        try:
            if component["PRIO"] != 0:  # check only sub-models models
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

                component.rotation_euler = rotate
                # Apply submodel transformation
                offset = Vector((sub_model_pos[0], sub_model_pos[1], sub_model_pos[2]))
                component.location = offset
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
        component["PCB_Side"] = "T"
        component.location = Vector(
            (
                float(posx),
                float(posy),
                posz,
            )
        )
        component.rotation_euler = Vector((0, 0, radians(float(deg))))

    else:  # side == "B"
        component["PCB_Side"] = "B"
        component.location = Vector(
            (
                -float(posx),
                float(posy),
                posz,
            )
        )
        component.rotation_euler = Vector((radians(180), 0, radians(float(deg))))

    bpy.ops.object.select_all(action="DESELECT")

    component.location += Vector([-pcb.dimensions.x / 2, -pcb.dimensions.y / 2, 0])
    cu.recalc_normals(component)

    # adding submodels for footprints with several 3D models
    if config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"] and "PRIO" in list(component.keys()):
        logger.debug(f"'{name}' keys: {list(component.keys())}")
        logger.debug(f"PRIO value: {component['PRIO']}")
        if component["PRIO"] != 0:  # check only main models
            return
        sub_param_count = 4  # number of parameters which define sub-model
        main_param_count = 3  # number of parameters which define main model
        substract_params = len(list(component.keys())) - main_param_count  # number of submodels parameters
        if "cycles" in component.keys():
            substract_params -= 1  # omit unknown 'cycles' property not generated by us
        submodel_count = ceil(substract_params / sub_param_count)  # assumed number of submodels
        if submodel_count == 0:  # if no submodels
            return
        logger.debug("Importing sub-models...")
        logger.debug(f"Number of sub-models count: {submodel_count}")
        for j in range(1, submodel_count + 1):
            submodel_original_name = f"{str(j)}_MODEL_NAME"
            # get name of 3D submodel
            if submodel_original_name not in component.keys():
                logger.debug("Missing data about submodels")
                continue
            submodel_footprint = component[submodel_original_name]
            submodel_name = name + f"_{str(j)}_submodel"
            # get translation and rotation of submodel
            submodel_pos = component[f"{str(j)}_{submodel_footprint}_POS"]
            submodel_rotate = component[f"{str(j)}_{submodel_footprint}_ROTATE"]
            import_comp(
                importer,
                pcb,
                submodel_footprint,
                submodel_name,
                posx,
                posy,
                side,
                deg,
                total_thickness,
                submodel_pos,
                submodel_rotate,
            )


def remove_duplicated_materials():
    """Remove duplicated materials across components."""
    logger.debug("Removing materials duplicates")

    materials_names = sorted([(mat.name.replace(" ", ""), mat.name) for mat in bpy.data.materials])
    original_name = materials_names[0][1]

    for i in range(len(materials_names)):
        name = materials_names[i][1]
        if "." not in name:  # original
            original_name = name
        else:  # duplicate
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

                bpy.data.materials.remove(bpy.data.materials[name])
