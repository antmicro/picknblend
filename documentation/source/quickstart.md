# Quick start

This scenario will generate a 3D model of the Open Source [Jetson Orin Baseboard](https://github.com/antmicro/jetson-orin-baseboard) populated with components as an example.
This guide uses the [`gerber2blend`](https://github.com/antmicro/gerber2blend) tool to prepare the base PCB model.

## Clone the board

```bash
git clone https://github.com/antmicro/jetson-orin-baseboard.git
```

## Clone the 3D model library

```bash
git clone https://github.com/antmicro/hardware-components.git
```

In order for the library to be visible by `picknblend`, specify it in the environment variable `MODEL_LIBRARY_PATHS`:

```bash
export MODEL_LIBRARY_PATHS=path/to/library/directory/hardware-components/
```

Alternatively, you can provide this path in the `blendcfg.yaml` file:

```bash
MODEL_LIBRARY_PATHS:
      - path/to/library/directory/hardware-components/
```

## Install KiCad

The open source EDA tool, [KiCad](https://www.kicad.org/), will be used for exporting input files for the board.
KiCad (from version 7.0.0 up) provides a CLI that can be used in the command line and CI environment.
To install KiCad run:

```bash
sudo apt install kicad
```

## Prepare input files from the hardware design

To generate a 3D model of the PCB, `gerber2blend` requires Gerber files and `picknblend` requires PnP data (and optionally BOM).

To generate Gerber files, run:

```bash
cd jetson-orin-baseboard  
mkdir fab
kicad-cli pcb export gerbers --no-protel-ext -o fab/ jetson-orin-baseboard.kicad_pcb
kicad-cli pcb export drill --format gerber --excellon-separate-th -o fab/ jetson-orin-baseboard.kicad_pcb
```

To generate PnP data in CSV format, run:

```bash
kicad-cli pcb export pos jetson-orin-baseboard.kicad_pcb -o fab/jetson-orin-baseboard-pos.csv --format csv --units mm --side both --use-drill-file-origin --bottom-negate-x
```

## Generate PCB Blender model

Use the [`gerber2blend`](https://github.com/antmicro/gerber2blend) tool to generate a Blender model of the PCB:

```bash
cd jetson-orin-baseboard
gerber2blend
```

Refer to `gerber2blend`'s [Quick start](https://antmicro.github.io/gerber2blend/quickstart.html) guide for detailed instructions.

## Populate PCB model with components using `picknblend`

In order to populate an already existing PCB model with components from PnP files, run:

```bash
picknblend
```

To preview the generated `.blend` file with populated components, open it with an instance of Blender in version >=4.1.