from dataclasses import dataclass, field
from typing import List, Dict, cast
from collections import defaultdict
from math import radians
from mathutils import Vector, Euler
import bpy
import logging
import re
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
    pnp_list: List[pnp.ComponentData] = field(default_factory=list)
    """PNP data"""
    override_data: Dict[str, pnp.ComponentData] = field(default_factory=dict)
    """optional override data to PNP input"""

    # Modified by the importer

    models_imported: list[str] = field(default_factory=list)
    """List of models that were imported (object names)."""
    model_summary: defaultdict[str, int] = field(default_factory=lambda: defaultdict(int))
    """Summary of imported models per-library."""


def import_all_components(board_col: bpy.types.Collection, board_thickness: float) -> None:
    """Import all components from PNP data and put them on the board."""
    if bpy.data.collections.get("Components"):
        logger.info("Components already imported.")
        return
    logger.info("Importing components.")

    # prepare input data
    importer = ImporterData()
    importer.marking_id_data = bom.parse_markings(config.bom_path)
    importer.blend_models_list = library.get_available_models()
    importer.pnp_list = pnp.get_pnp_files(config.fab_path)

    override_file = fio.find_file_in_fab("override.csv")
    if override_file is not None:
        importer.override_data = pnp.get_override_file(config.fab_path, override_file)
    main_col = bpy.data.collections.get(config.PCB_name)
    cu.create_collection("Components", main_col)
    if config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"]:
        cu.create_collection("Misc", main_col)

    # process all components import
    process_components_import(
        importer,
        board_col.objects[-1],
        board_thickness,
    )

    # cleanup after import
    cu.remove_collection(["Temp"])
    remove_duplicated_materials()

    logger.info("Component blender models summary:")
    for key in importer.model_summary:
        logger.info(key + " = " + str(importer.model_summary[key]))

    for collection in bpy.data.collections:
        if "Collection" in collection.name:
            bpy.data.collections.remove(collection)


def process_components_import(
    importer: ImporterData,
    pcb: bpy.types.Object,
    board_thickness: float = 0,
) -> None:
    """Import components from parsed PNP files onto the specified PCB object."""
    for component in importer.pnp_list:
        importer.model_summary["total_models"] += 1
        ref_prefix = component.reference.strip("0123456789")
        if not config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"] and ref_prefix == "A":
            continue

        pkg = component.footprint
        name = component.reference + ":" + component.value
        # check and apply component's position and name override from override file
        ref_pkg = f"{component.reference}-{pkg}"
        override_element = None

        if ref_pkg in importer.override_data:
            override_element = importer.override_data[ref_pkg]
            logger.debug(f"Using override for designator {component.reference} with values: {override_element}")
        elif pkg in importer.override_data:
            override_element = importer.override_data[pkg]
            logger.debug(f"Using override for footprint {pkg} with values: {override_element}")
        if override_element:
            component.pos_x += override_element.pos_x
            component.pos_y += override_element.pos_y
            component.rot += override_element.rot
            if override_element.override != "":
                pkg = override_element.override
            if override_element.side == "flip":
                component.side = "T" if component.side == "B" else "B"
                component.pos_x *= -1

        pos_z = 0 if component.side == "B" else board_thickness
        # check if markings used
        if config.blendcfg["EFFECTS"]["SHOW_MARKINGS"]:
            if component.reference not in importer.marking_id_data:
                logger.debug(f"Footprint {pkg} for {component.reference} not found in BOM file. Ignoring marking")
            elif f"{pkg}-{importer.marking_id_data[component.reference]}" in importer.blend_models_list:
                ahid = importer.marking_id_data[component.reference]
                pkg = f"{pkg}-{ahid}"
                logger.info(f"Importing {name}: {pkg} with marking")

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
            component.pos_x,
            component.pos_y,
            component.side,
            component.rot,
            pos_z,
        )

    cu.parent_collection_to_object("Components", pcb)
    if config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"]:
        cu.parent_collection_to_object("Misc", pcb)


def create_component(importer: ImporterData, footprint: str) -> bpy.types.Object | None:
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
        if component is None:
            return None

        # Name the component based on shortened footprint name
        # This is used to later be able to duplicate already imported models.
        component.name = obj_name
        temp_coll = cu.create_collection("Temp")
        cu.link_obj_to_collection(component, temp_coll)
        importer.models_imported.append(obj_name)

        logger.debug(f"Imported new model for footprint: {obj_name} and moved to Temp collection")

        # Copy the component - this one will be actually placed on the board
        return cast(bpy.types.Object, component.copy())
    logger.debug(f"Duplicated already imported model for footprint: {footprint}")
    bpy.ops.object.select_all(action="DESELECT")
    return cast(bpy.types.Object, bpy.data.objects[obj_name].copy())


def import_comp(
    importer: ImporterData,
    pcb: bpy.types.Object,
    footprint: str,
    name: str,
    posx: float,
    posy: float,
    side: str,
    deg: float,
    board_thickness: float,
    sub_model_pos: List[float] = [0, 0, 0],
    sub_model_rot: List[float] = [0, 0, 0],
) -> None:
    """Import a component onto the PCB.

    Import a single component with `footprint` onto the specified `pcb` object.
    When looking up models for the footprint, mappings from the `importer` class
    are used.
    """
    if side != "T" and side != "B":
        logger.error("unknown side: " + str(side))
        return

    pos_z = board_thickness
    component = create_component(importer, footprint)
    if component is None:
        return
    component.name = name

    if "PRIO" in component.keys():  # type: ignore
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
                logger.debug(f"Submodel import position: [{sub_model_pos[0]}, {sub_model_pos[1]}, {sub_model_pos[2]}]")
                logger.debug(f"Submodel import rotation: [{sub_model_rot[0]}, {sub_model_rot[1]}, {sub_model_rot[2]}]")
                rotate = Euler(
                    (
                        radians(sub_model_rot[0]),
                        radians(sub_model_rot[1]),
                        radians(sub_model_rot[2]),
                    )
                )  # type: ignore

                component.rotation_euler = rotate
                offset = Vector((sub_model_pos[0], sub_model_pos[1], sub_model_pos[2]))  # type: ignore
                component.location = offset
        except Exception as e:
            logger.debug(f"Model {footprint} does not have PRIO custom property. {e}")

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
                posx,
                posy,
                pos_z,
            )
        )  # type: ignore
        component.rotation_euler = Euler((0, 0, radians(float(deg))))  # type: ignore

    else:  # side == "B"
        component["PCB_Side"] = "B"
        component.location = Vector(
            (
                -posx,
                posy,
                pos_z,
            )
        )  # type: ignore
        component.rotation_euler = Euler((radians(180), 0, radians(float(deg))))  # type: ignore

    bpy.ops.object.select_all(action="DESELECT")

    component.location += Vector([-pcb.dimensions.x / 2, -pcb.dimensions.y / 2, 0])  # type: ignore
    cu.recalc_normals(component)

    # add submodels for footprints with several 3D models
    if config.blendcfg["EFFECTS"]["SHOW_MECHANICAL"] and "PRIO" in list(component.keys()):  # type: ignore
        logger.debug(f"'{name}' keys: {list(component.keys())}")  # type: ignore
        logger.debug(f"PRIO value: {component['PRIO']}")

        if component["PRIO"] != 0:  # check only main models
            return

        submodels = parse_submodel_properties(component)
        if not submodels:
            return

        logger.debug("Importing submodels...")
        logger.debug(f"Submodels count: {len(submodels)}")
        for idx, (submodel, value) in enumerate(submodels.items()):
            submodel_name = name + f"_{idx}_submodel"
            import_comp(
                importer,
                pcb,
                submodel,
                submodel_name,
                posx,
                posy,
                side,
                deg,
                board_thickness,
                value["POS"],
                value["ROTATE"],
            )


def parse_submodel_properties(component: bpy.types.Object) -> Dict[str, Dict[str, List[float]]]:
    """Parse object's custom properties in search of sub-models' definition."""
    pattern = r"^\d+_(.*)_(ROTATE|POS|MODEL_NAME)$"
    submodel_data: dict[str, dict[str, List[float]]] = {}
    for key, value in component.items():  # type: ignore
        match = re.match(pattern, key)
        if match:
            model_number = match.group(1)
            prop_type = match.group(2)
            if model_number not in submodel_data:
                submodel_data[model_number] = {}
            submodel_data[model_number][prop_type] = cast(List[float], value)
    return submodel_data


def remove_duplicated_materials() -> None:
    """Remove duplicated materials across components."""
    logger.debug("Removing materials duplicates")

    materials_names = sorted([(mat.name.replace(" ", ""), mat.name) for mat in bpy.data.materials])
    original_name = materials_names[0][1]

    for i in range(len(materials_names)):
        name = materials_names[i][1]
        if "." not in name:  # original
            original_name = name
        else:
            if (original_name + ".") in name:
                original_material = bpy.data.materials[original_name]

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
