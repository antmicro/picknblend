# Installation

## Install dependencies

To install dependencies for `picknblend` on a Debian/Ubuntu-based system, run the following commands:

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv pipx git libsm6
```

## Configure PATH

Make sure that the directory `/home/[username]/.local/bin` is present in your `PATH`.
You can do this by running the following in your shell:

```bash
export PATH=$HOME/.local/bin:$PATH
```

## Clone and install `picknblend`

Install `picknblend`:

```bash
python3.11 -m pipx install 'git+https://github.com/antmicro/picknblend.git'
```

```{note}
For developers, it is recommended to clone the repository and install picknblend in editable mode:

    git clone https://github.com/antmicro/picknblend.git
    cd picknblend
    python3.11 -m pipx install --editable .

```

This installs the required dependencies and installs `picknblend` into its own virtual environment.
`picknblend` depends on the `bpy` package in version `4.1` to interact with Blender, which is currently only compatible with Python 3.11.
