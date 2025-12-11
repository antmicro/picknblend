# Introduction

`picknblend` is a tool created to automate component placement onto a PCB 3D model.
This tool works in conjunction with [gerber2blend](https://antmicro.github.io/gerber2blend/), enabling creation of Blender PCB models populated with electrical and mechanical components.
`picknblend` uses Pick and Place (PnP) fabrication outputs to import individual component models onto a board model.
The tool is compatible with designs created using a variety of EDA (Electronic Design Automation) software.

* [Installation](install.md) describes the installation process.
* [Quick start](quickstart.md) presents a simple example of script usage based on Antmicro's open source [Jetson Orin Baseboard](https://github.com/antmicro/jetson-orin-baseboard).
* [Usage](usage.md) describes basic usage and features of the tool.
* [Configuring blendcfg.yaml](blendcfg.md) presents configuration options available for customizing the processing workflow.
