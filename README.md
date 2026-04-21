# DBC to C Library Generator

This project is a Python-based tool that parses DBC (CAN database) files and generates a C or C++ library for handling CAN messages and signals.

## ✨ Features

- Parses DBC files using the [`cantools`](https://github.com/eerimoq/cantools) library.
- Generates type-safe and structured C and C++ libraries using Jinja2 templates.
- Supports signal decoding/encoding, raw values, scaling, offset, and sign extension.
- Generates fully featured APIs including RX/TX processing modes.
- Provides an automated test pipeline for verifying both C and C++ generated libraries.
- Cross-platform support (Windows, Linux, macOS via GCC/MinGW).

## 🛠 Requirements
- [`Python 3.13+`](https://www.python.org/)

## 📦 Installation

### 1. Clone the repository

```sh
git clone <repository-url>
cd <repository-name>
```

### 2. Install dependencies

```sh
pip install -r requirements.txt
```

## 🚀 Usage

## Generate a library from a DBC file:
We recommend using official Release to run the program.

**Or use this command tu run the App:**
```sh
python -m src.canlibrarygenerator
```

Follow the prompt to select `.dbc` file. The generated library will be saved in a folder of your choice.

## Generated Files
Both C and C++ generators now share the same architecture and create the following structure (extensions are `.h`/`.c` for C and `.hpp`/`.cpp` for C++):
```graphql
├── <prefix>/                   # Root folder for generated libraries
    ├── inc/                        # Folder with header files
    |   ├── can_db_def.h(.hpp)                # Header file with base Message/Signal structure (use only once in whole project)
    |   ├── <prefix>_db.h(.hpp)               # Header file with Messages and Signals structures
    |   └── <prefix>_interface.h(.hpp)        # Header file with functions for unpackage/package and input/output process
    └── src/                        # Folder with source files
        ├── <prefix>_db.c(.cpp)               # Source file with declaration of Messages and Signals
        └── <prefix>_interface.c(.cpp)        # Source file with declaration of  functions for unpackage/package and input/output process
```

## 🧪 Test Pipeline (Automatic after every commit in certain branches)
```sh
python src/canlibrarygenerator/test/test_pipeline.py
```
The pipeline will:
- Generate the code from an example DBC file.
- Compile the generated C and C++ code using gcc/g++.
- Run example test applications.
- Check that unpacking and packing (e.g. <prefix>_unpackage_message(), <prefix>_package_message()) works correctly with data integrity tests.

## 🧹 Cleaning Up
All generated files during tests are stored in the `temp/` directory and are automatically cleaned after the test pipeline finishes.

## 📁 Project structure
```graphql
├── docs/                           # Documentation files
├── src/                            # Source files
|   ├── canlibrarygenerator/           # Main project folder
|   |   ├── dbc/                           # DBC files
|   |   |   └── CAN_example.dbc
|   |   ├── generate_functions/            # Scripts for generating libraries
|   |   |   ├── generate_c_library.py
|   |   |   └── generate_cpp_library.py
|   |   ├── ir/                            # Intermediate Representation (builder, models)
|   |   |   ├── builder.py
|   |   |   └── models.py
|   |   ├── png/                           # Images
|   |   |   └── VSB-TUO_logo.png
|   |   ├── renderers/                     # Jinja2 template renderers
|   |   |   ├── c_renderer.py
|   |   |   └── cpp_renderer.py
|   |   ├── resources/                     # Folder with resources for building project
|   |   |   └── icon/                          # Folder with icon images
|   |   |       |   icon.icns
|   |   |       |   icon.ico
|   |   |       └── icon-64.png
|   |   ├── scripts/                       # Additional scripts
|   |   |   |   codegen_utils.py
|   |   |   |   delete_temp_files.py
|   |   |   |   generate_source_files.py
|   |   |   └── inject_version.py
|   |   ├── templates/                     # Jinja2 templates (c/ and cpp/)
|   |   ├── test/                          # Test applications
|   |   |   ├── test_c.c
|   |   |   ├── test_cpp.cpp
|   |   |   └── test_pipeline.py
|   |   ├── utils/                         # CAN utilities
|   |   |   └── can_utils.py
|   |   ├── __init__.py
|   |   └── __main__.py                    # DBC to code generator
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── README.md
└── requirements.txt
```

## 📝 License
This project is licensed under the <b>MIT Licence</b>

## 📫 Contact
For issues or questions, open [issue on GitHub](https://github.com/mobility-lab-vsb/can-library-generator/issues).