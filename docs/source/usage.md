# Usage

To run `picknblend`, execute:

```bash
picknblend
```

Since `picknblend` requires a config `blendcfg.yml` file in the project's directory, the command will add a default version of the file (provided one is not present) and run the tool's script.

To add the configuration file without running the script, execute:

```bash
picknblend -g
```

Running the command above will overwrite any existing config file.

The default configuration file can be adjusted to match a project, for example to add a library directory or change input directory names.

## Required input files

By default, `picknblend` operates on fabrication outputs found in the `fab/` subdirectory in the directory from which the tool is executed.
In order to generate a model, first create a `fab/` directory:

```bash
cd [path to project repository]/
mkdir fab/
```

`picknblend` requires the following input files:

* A Blender model of a board in `.blend` format (for detailed specification, see: [Blender board model](#blender-board-model)). You can use [gerber2blend](https://antmicro.github.io/gerber2blend/index.html) complementary tool to generate it.
* Pick and Place (PnP) data from a hardware project in `.csv` format
* A library of component 3D models in `.blend` format. We suggest using [Antmicro Hardware Components](https://github.com/antmicro/hardware-components).
* (Optional) A Bill of Materials (BOM) from a hardware project (required for importing models with markings that use the `SHOW_MARKINGS` `blendcfg.yaml` setting).

### Blender board model

`picknblend` will recognize a Blender model as a correct board model when the following collection structure is defined:

* **root collection** - named the same as the `.blend` file. If `gerber2blend` was used to generate the model, it will be the same as project name. If the project name weren't sourced, it will be `unknownpcb`.
* **child collection** - named `Board`, containing a PCB object named the same as the root collection.

### PnP data

The `picknblend` script can parse PnP data in `.csv` format from the `fab/` directory of the current hardware project (default) or the directory specified in the `FAB_DIR` setting in `blendcfg.yaml`.
CSV files will be recognized as PnP data if they end with the `*pos.csv` suffix.
`picknblend` can parse either separate side position files or a combined one.  

The CSV file must contain columns specified below.
The order of the columns in the position file is not relevant.
In order to support many EDA standards, multiple column names are accepted.

* reference designator (allowed column names: `Ref`, `Designator`)
* symbol name (allowed column names: `Val`, `Comment`)
* footprint name (allowed column names: `Package`, `Footprint`)
* position in X axis (allowed column names: `PosX`, `X`)
* position in Y axis (allowed column names: `PosY`, `Y`)
* rotation in Z axis (allowed column names: `Rot`, `Rotation`)
* side of PCB (allowed column names: `Side`, `Layer`) with possible values: `T`, `top`,`Top`,`TopLayer`,`B`,`bottom`,`Bottom`,`BottomLayer`

```{note}
To change the parsable column names and top/bottom side values, you can edit the `pnp.py` module.
```

### Component library

The `picknblend` script will use a Blender model component library that follows these guidelines:

* **directory structure** - any directory containing Blender models can serve as a library, with `.blend` files searched recursively.
* **model naming conventions** - as `picknblend` supports importing generic and detailed models with part-specific markings, the following naming conventions must be followed:
  * generic parts - `<footprint>.blend` (e.g. `0603_res.blend`)
  * parts with markings - `<footprint>-<manufacturer>-<mpn>.blend`, where `<manufacturer>-<mpn>` part is slugified (e.g. `0603_res-yageo-rc0603jr0710k.blend`)
* **model structure** - each `.blend` file must contain a single object under a single collection.

The paths to model libraries are configured via the `blendcfg.yaml` configuration file.
Specifically, the `MODEL_LIBRARY_PATHS` field defines where the script will search for models.
Libraries will be searched top-to-bottom as listed in `MODEL_LIBRARY_PATHS`.
If a model with a given footprint exists in multiple libraries, the first library (top-most) in the list will take priority, preventing models from deeper libraries from being loaded for that footprint.

Additionally libraries can be included by modifying the `MODEL_LIBRARY_PATHS` environment variable.
This environment variable accepts a PATH-style `:`-delimited list of directories that should be prepended to the search path, meaning they will be searched before any paths defined in `blendcfg.yaml`.
The order in which directories are listed in `MODEL_LIBRARY_PATHS` will dictate their search priority.

## Optional input files

### Bill of Materials

A BOM is required when markings on chips are enabled in the configuration.
The BOM needs to come in `.csv` format and contain the following columns:

* Manufacturer (allowed column names: `Manufacturer`, `Mfr`)
* Manufacturer Part Number (allowed column names: `MPN`)
* Footprint (allowed column names: `Footprint`, `Package`)
* Reference (allowed column names: `Ref`, `Reference`, `Designator`)

```{note}
To change the parsable column names, edit the `bom.py` module.
```

Additional requirements for the BOM file:

* The first row in the file must contain the names of columns; any additional info on top of the document must be removed (as some EDAs generate BOM files).
* Values in `Reference` fields must be separated with a space, not a comma.
* `Footprint` fields must contain only the name of a footprint; the library name must be removed (if generated by EDA).

The order of columns in the BOM file is not relevant and additional columns in the file are allowed.

In order to generate a BOM file in KiCad, follow the [KiCad documentation](https://docs.kicad.org/7.0/en/eeschema/eeschema_generating_outputs.html#bom-export) with a default `bom_csv_grouped_by_value` generator script.
Then adjust the file to the requirements mentioned above.

### PnP override file

The PnP override file allows you to define footprint names and position adjustments for component models on the PCB when importing PNP data exported from EDA software.
This file should be placed in the same directory as the PnP files and `picknblend` will automatically recognize it if its name ends with the `override.csv` suffix.
The override file must follow the same column structure as the PnP file.
For specifying footprint name override, add new column `Override`. 

Guidelines for preparing the override file:

* Overrides can be applied to individual components by listing their reference designators in the `Ref` column (separated by spaces if more than one).
* Leaving the `Ref` column empty will apply the override to all components with the specified footprint name.
* If no override is required for a footprint, it can be omitted from the file.
* To override footprint name, specify new name in `Override` column.
* New footprint name will be also applied when searching for a model with marking.
* Define position overrides in the `PosX`, `PosY`, and `Rotation` columns with the required values or leave cells empty for values that don't need adjustment.
* To move a component to the opposite side of the PCB, in the `Side` column set `flip` or leave it empty if no change is needed.

## Importing submodels

By default, `picknblend` does not put any additional mechanical objects to the board objects if the switch `SHOW_MECHANICAL` in the `blendcfg.yml` file is not set to `True`.
The two existing ways to specify a mechanical object on the board are described in the sections below.

### Components with reference designator `A`

As long as component in the PnP file has a designator `A`, it won't show up without setting the `SHOW_MECHANICAL` switch.

### Models specified as sub-models in imported `.blend` files

It is possible to define a model within a model, for instance a `PLUG_USB-C.blend` model within a `RECEPTACLE_USB-C.blend` model.
All models defined this way will be treated as a sub-models and won't show up without setting the `SHOW_MECHANICAL` switch.
In order to define the `PLUG_USB-C.blend` sub-model within the `RECEPTACLE_USB-C.blend` model, follow the instructions:

1. Open `PLUG_USB-C.blend` using Blender.
1. In the `Properties` area, go to the `Custom Properties` section within the `Object Properties` tab.
1. Add a `PRIO` property with an integer value larger than zero - it will indicate to the script that this is a sub-model.
1. Save and close the file.
1. Open `RECEPTACLE_USB-C.blend` using Blender.
1. In the `Properties` area, go to the `Custom Properties` section within `Object Properties` tab.
1. Add a `PRIO` property with an integer value of `0` (zero) - it will indicate to the script that this is the main model.
1. Add a `1_MODEL_NAME` property with a string value of `PLUG_USB-C`, defining the name of the sub-model file.
1. Add a `1_PLUG_USB-C_POS` property with float array values defining the X, Y and Z positions of the sub-model in respect to main model's origin.
1. Add a `1_PLUG_USB-C_ROTATE` property with float array values defining the X, Y and Z rotation of the sub-model in respect to main model's origin.
1. Save and close the file.

If the main model should contain more sub-models, simply add more custom properties with appropriate names and values. As an example, a double USB connector should contain the following properties:
[`PRIO`, `1_MODEL_NAME`, `1_<MODEL_1_NAME>_POS`, `1_<MODEL_1_NAME>_ROTATE`, `2_MODEL_NAME`, `2_<MODEL_2_NAME>_POS`, `2_<MODEL_2_NAME>_ROTATE`].

## Outputs

The resulting PCB model file, `<project-name>.blend`, with components placed on it, is saved in `[path to project repository]/fab/`.
It overwrites the initial file containing the PCB model.
All imported components will be added to the `Components` collection, under the `<project-name>` root collection.
Components will be parented to the PCB model, so that PCB translations affect components as well.

## CLI arguments

`picknblend` supports the following command line arguments:

* `-d` - enables debug logging
* `-r` - re-imports all components in the already existing `fab/<project-name>.blend` file
* `-c CONFIG_PRESET` - uses a selected `blendcfg` preset
* `-b BLEND_PATH` - specifies a path to file, if different from the project file
* `-g` - copies `blendcfg.yaml` file from template into current working directory. This will overwrite the existing config file.
