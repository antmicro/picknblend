"""Schema for gerber2blend configuration file"""

from marshmallow import fields  # type: ignore
from marshmallow import fields, Schema, EXCLUDE  # type: ignore
from typing import Any


class BaseSchema(Schema):
    """
    A base schema for configuration definitions.
    This schema ensures that:
    - unknown fields are ignored during deserialization and not included in the parsed config
    - the schema is used only for loading (all fields are marked as `load_only`)
    - all fields are required, enforcing strict input validation
    """

    class Meta:
        unknown = EXCLUDE

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        for field in self.declared_fields.values():
            field.load_only = True
            field.required = True


def get_schema_field(schema_class: type[BaseSchema], field_name: str) -> fields.Field:
    """Get declared schema field by name."""
    try:
        schema_field = schema_class._declared_fields[field_name]
        return schema_field
    except KeyError:
        raise RuntimeError(f"Schema field '{field_name}' could not be found in {schema_class.__name__}")


class SettingsSchema(BaseSchema):
    PRJ_EXTENSION = fields.String()
    FAB_DIR = fields.String()
    BOM_DIR = fields.String()
    MODEL_LIBRARY_PATHS = fields.List(fields.String())
    APPLY_TRANSFORMS = fields.Bool()


class EffectsSchema(BaseSchema):
    SHOW_MECHANICAL = fields.Bool()
    SHOW_MARKINGS = fields.Bool()


class ConfigurationSchema(BaseSchema):
    """Parent schema for configuration file"""

    SETTINGS = fields.Nested(SettingsSchema)
    EFFECTS = fields.Nested(EffectsSchema)
