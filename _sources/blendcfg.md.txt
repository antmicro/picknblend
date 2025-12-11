# Configuring blendcfg.yaml

You can customize `picknblend`'s behavior and outputs by editing the `blendcfg.yaml` file which defines component import options.
The file needs to be placed in the main directory of the hardware project.
A default `blendcfg.yaml` is generated in the project directory when one does not exist.
Alternatively it can be copied manually from this repo, from the [`templates/blendcfg.yaml`](../../src/picknblend/templates/blendcfg.yaml) file.

A single, joint `blendcfg.yaml` file can be shared between [`gerber2blend`](https://github.com/antmicro/gerber2blend) and `picknblend` tools.

This file can contain the following configuration sections:

### `SETTINGS`

Specifies paths to input files and naming conventions used by `picknblend`:

* `FAB_DIR` - string specifying the **name** of the intermediate work directory that the board model and PnP data are located in. This is relative to the working directory/hardware project that `picknblend` is executed from.
* `BOM_DIR` - string specifying the **name** of the directory the Bill of Materials (BOM) data is located in. This is relative to the working directory/hardware project that `picknblend` is executed from. The BOM is assumed to be in a filename suffixed with `BOM-populated.csv`. BOM is only required when the `SHOW_MARKINGS` option is enabled.
* `PRJ_EXTENSION` - string containing EDA software main project file extension, used to read the PCB project name. Can be set to `""` if the extension is undefined. If no files with this extension are found, `unknownpcb` will be used as the name.
* `MODEL_LIBRARY_PATHS` - array of strings containing paths to model libraries (simple directories containing `.blend` files) that will be used during import. The paths can contain environment variables (using the `$NAME` or `${NAME}` syntax) that will be expanded by `picknblend` at startup. Model libraries are searched from top to bottom, where libraries appearing earlier in the `MODEL_LIBRARY_PATHS` have priority over later ones.

### `EFFECTS`

Enables additional import effects:

* `SHOW_MECHANICAL` - boolean switch enabling mechanical components import. See [Importing submodels](usage.md#importing-submodels) chapter for more info about defining mechanical components.
* `SHOW_MARKINGS` - boolean switch that enables importing models with part-specific markings. When enabled, BOM data must be provided. The manufacturer and MPN from the BOM will be used when determining the model to import instead of using a generic footprint model.

## Custom config settings

`picknblend` can run with a specified configuration preset by typing `picknblend -c custom_preset` as mentioned in the [usage chapter](usage.md#additional-cli-arguments). 
The current template file contains a single, default preset. You can add a new preset and save it in the `blendcfg.yaml` template file as follows:

```yaml
default:
    SETTINGS:
        FAB_DIR: fab
        BOM_DIR: doc
        PRJ_EXTENSION: .kicad_pro
...

custom_preset:
    SETTINGS:
        FAB_DIR: fabrication_dir
        BOM_DIR: bom_dir
```

In `blendcfg.yaml` presets, only the fields that are modified need to be included in a new preset.
The remaining values are inherited from the default preset through mapping merges.