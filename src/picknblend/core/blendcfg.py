"""Module responsible for parsing config file."""

import logging
import os.path
from shutil import copyfile
from typing import Any, Callable, Dict, Optional
import hiyapyco  # type: ignore

logger = logging.getLogger(__name__)

# Name of the configuration file
# This is the name that is used for the template
# and when copying the template to a local config.
BLENDCFG_FILENAME = "blendcfg.yaml"


class Field:
    """Represents schema of a configuration field."""

    def __init__(
        self,
        field_type: str,
        conv: Optional[Callable[[Any], Any]] = None,
        optional: bool = False,
    ) -> None:
        """Create a configuration field.

        Args:
        ----
            field_type: String name of the type of the field. One of: "color",
                "background", "bool", "number", "color_preset", "transition".
            conv: Converter function to use. When set, the value of the field from
                `blendcfg.yaml` is passed to this function. Value returned from
                the function is still checked against the field's specified type.
            optional: Specify if the field can be omitted from the blendcfg. Optional
                fields are set to None in the configuration if they are not
                present.

        """
        self.type = field_type
        self.conv = conv
        self.optional = optional


# Schema for blendcfg.yaml file
CONFIGURATION_SCHEMA = {
    "NAMING": {
        "FAB_DIR": Field("string"),
        "BOM_DIR": Field("string"),
        "PROJECT_EXTENSION": Field("string"),
        "MODEL_LIBRARY_PATHS": Field("list[str]"),
    },
    "EFFECTS": {
        "SHOW_MECHANICAL": Field("bool"),
        "SHOW_MARKINGS": Field("bool"),
    },
}


def check_and_copy_blendcfg(file_path: str, pnb_path: str, force: bool = False) -> None:
    """Copy blendcfg to project's directory."""
    if not os.path.exists(file_path + BLENDCFG_FILENAME) or force:
        prompt = "enforced copy" if force else "no config found in working directory"
        logger.warning(f"Copying default config from template ({prompt})")
        copyfile(pnb_path + "/templates/" + BLENDCFG_FILENAME, file_path + BLENDCFG_FILENAME)


def is_color(arg: str | None) -> bool:
    """Check if given string represents hex color."""
    hex_chars = "0123456789ABCDEF"
    if arg is None:
        return False
    return len(arg) == 6 and all([c in hex_chars for c in arg])


def is_color_preset(arg: str | list[str] | None) -> bool:
    """Check if given string represents preset color."""
    if arg is None:
        return False
    presets = ["White", "Black", "Blue", "Red", "Green"]  # allowed color keywords
    if isinstance(arg, list):
        arg = arg[0]
    if arg in presets:
        return True
    if is_color(arg):
        return True
    return False


def hex_to_rgba(hex_number: str, alpha: bool = True) -> tuple[float, ...]:
    """Convert hex number to RGBA."""
    rgb = []
    for i in (0, 2, 4):
        decimal = int(hex_number[i : i + 2], 16)
        rgb.append(decimal / 255)
    if alpha:
        rgb.append(1)
    return tuple(rgb)


def parse_strings(arg: str) -> list[str]:
    """Parse string and split into separate values by comma separator."""
    return arg.replace(",", "").split()


def check_throw_error(cfg: Dict[str, Any], args: list[str], schema: Field) -> None:
    """Validate the given configuration entry.

    Args:
    ----
        cfg: entire deserialized blendcfg.yaml file
        args: a list of names leading to the configuration entry that
              needs to be checked, for example: ["SETTINGS", "DPI"].
              Currently, there must be exactly two names present in the list!
        schema: schema for the field

    """
    missing_config = False
    val = None
    if cfg is None:
        missing_config = True

    if len(args) < 2:
        logger.error(f"[{args[0]}][{args[1]}] not found in {BLENDCFG_FILENAME}")
        raise RuntimeError("Configuration invalid")

    try:
        val = cfg.get(args[0], None)
        if val is None:
            raise Exception
        val = val.get(args[1], None)
    except Exception:
        missing_config = True

    if not schema.optional and (val is None or missing_config):
        logger.error(f"[{args[0]}][{args[1]}] not found in {BLENDCFG_FILENAME}")
        raise RuntimeError("Configuration invalid")

    # Short-circuit when the field is not required
    if val is None and schema.optional:
        cfg[args[0]][args[1]] = None
        return

    if schema.conv is not None:
        try:
            val = schema.conv(val)
            cfg[args[0]][args[1]] = val
        except Exception as e:
            logger.error(
                "Converting value [%s][%s] (= %s) failed: %e",
                args[0],
                args[1],
                val,
                str(e),
            )
            raise RuntimeError("Configuration invalid") from e

    not_schema_type_err = f"[{args[0]}][{args[1]}] is not a {schema.type}"
    color_type_err = f"[{args[0]}][{args[1]}] is not a color, should be hex color value"

    match schema.type:
        case "color":
            assert is_color(val), color_type_err
        case "bool":
            assert isinstance(val, bool), not_schema_type_err
        case "number":
            assert isinstance(val, float) or isinstance(val, int), not_schema_type_err
        case "color_preset":
            assert is_color_preset(val), color_type_err + " or presets"
        case "tuple":
            assert isinstance(val, tuple), not_schema_type_err
        case "string":
            assert isinstance(val, str), not_schema_type_err
        case "list[str]":
            assert isinstance(val, list), not_schema_type_err
            assert all(isinstance(x, str) for x in val), not_schema_type_err
        case _:
            raise RuntimeError(f"[{args[0]}][{args[1]}] is not a {schema.type}")


def validate_module_config(schema: dict[str, Field], conf: dict[str, Any], module_name: str) -> bool:
    """Validate the module config against a given schema.

    Returns
    -------
        True: module configuration is valid
        False: module configuration is invalid

    """
    valid = True

    for name, field in schema.items():
        try:
            check_throw_error(conf, [module_name, name], field)
        except Exception as e:
            logger.error("Field %s invalid: %s", name, str(e))
            valid = False

    return valid


def validate_setting_dependencies(cfg: Any) -> None:
    """Validate if certain blendcfg.yaml settings have their required dependencies."""
    _ = cfg
    pass
    # Left empty on purpose
    # If required, this can be expanded to include additional validation
    # for blencfg.yaml configuration entries, for example: a setting depends
    # on a different setting to be enabled.


def check_and_parse_blendcfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and parse the blendcfg.yaml loaded from a file."""
    valid = True

    for module in cfg:
        if module not in CONFIGURATION_SCHEMA:
            continue

        # Check config for module
        if not validate_module_config(CONFIGURATION_SCHEMA[module], cfg, module):
            valid = False

    if not valid:
        raise RuntimeError("Configuration in blendcfg.yaml invalid")

    validate_setting_dependencies(cfg)

    return cfg


def open_blendcfg(path: str, config_preset: str, pnb_path: str) -> Dict[str, Any]:
    """Open configuration file from the specified path."""
    cfg_path = path + "/" + BLENDCFG_FILENAME
    template_path = pnb_path + "/templates/" + BLENDCFG_FILENAME
    config = hiyapyco.load([template_path, cfg_path], method=hiyapyco.METHOD_MERGE)
    if config_preset not in config:
        raise RuntimeError(f"Unknown blendcfg preset: {config_preset}")
    return check_and_parse_blendcfg(config[config_preset])
