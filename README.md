# DBC to C Library Generator

This project is a Python-based tool that parses DBC (CAN database) files and generates a C or C++ library for handling CAN messages and signals.

## ✨ Features

- Parses DBC files using the [`cantools`](https://github.com/eerimoq/cantools) library.
- Generates type-safe and structured in C or C++.
- Supports signal decoding/encoding, raw values, scaling and offset.
- Provides a test pipeline for verifying generated libraries.
- Cross-platform support (Windows, Linux, macOS via GCC/MinGW)

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
Requires Python 3.10+ and `gcc` and `g++` installed in PATH.

## 🚀 Usage

## Generate a library from a DBC file:
```sh
python main.py
```
Follow the prompt to select `.dbc` file. The generated library will be saved in a folder of your choice.

## Generated Files
The script creates the following:

- `your_library.h` - Header file with `DBCMessage` and `DBCSignal` structures.
- `your_library.c` - Implementation for decoding and parsing CAN message.
- *(if using C++ mode)* `your_library.hpp` and `your_library.cpp` with moder classes and vector support.

## 🧪 Test Pipeline (Automatic after every commit)
```sh
python test_pipeline.py
```
The pipeline will:
- Compile the generated code.
- Run example test applications.
- Check that unpacking and packing (e.g. `dbc_unpackage_message()`, `dbc_package_message()`) works correctly.
- Clean up temporary files in the `temp/` directory.

Test data and messages are defined in `test_pipeline.py`.

## 🛠 Requirements
- Python 3.10+
- [`cantools`](https://github.com/eerimoq/cantools)
- [`darkdetect`](https://github.com/albertosottile/darkdetect)
- [`sv_ttk`](https://github.com/rdbende/Sun-Valley-ttk-theme)
- GCC or MinGW (for Windows)

## 🧹 Cleaning Up
All generated files are stored in the `temp/` directory and are automatically cleaned after testing.

## 📁 Project structure
```graphql
├── src/                            # Source files
|   ├── dbc/                           # DBC files
|   |   └── CAN_example.dbc
|   ├── generate_functions/            # Scripts for generating libraries
|   |   ├── generate_c_library.py
|   |   └── generate_cpp_library.py
|   ├── png/                           # Images
|   |   ├── checked.png
|   |   ├── tristate.png
|   |   ├── unchecked.png
|   |   └── VSB-TUO_logo.png
|   ├── test/                          # Test applications
|   |   ├── test_c.c
|   |   ├── test_cpp.cpp
|   |   └── test_pipeline.py
|   └── ttkwidget/                     # CheckboxTreeview class
|       └── checkboxtreeview.py
├── main.py                         # DBC to code generator
├── README.md
├── requirements.txt
└── setup.py
```

## 📝 License
This project is licensed under the <b>MIT Licence</b>

## 📫 Contact
For issues or questions, open [issue on GitHub](https://github.com/mobility-lab-vsb/can-library-generator/issues).