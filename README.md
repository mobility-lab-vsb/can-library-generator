# DBC to C Library Generator

This project is a Python-based tool that parses DBC (CAN database) files and generates a C or C++ library for handling CAN messages and signals.

## ✨ Features

- Parses DBC files using the [`cantools`](https://github.com/eerimoq/cantools) library.
- Generates type-safe and structured in C or C++.
- Supports signal decoding, raw values, scaling and offset.
- Provides a test pipeline for verifying generated libraries.
- Cross-platform support (Windows, Linux via GCC/MinGW)

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

## 🧪 Test Pipeline
```sh
python test_pipeline.py
```
The pipeline will:
- Compile the generated code.
- Run example test applications.
- Check that decoding (e.g. `dbc_decode_message()`) works correctly.
- Clean up temporary files in the `temp/` directory.

Test data and messages are defined in `test_pipeline.py`.

## 🛠 Requirements
- Python 3.10+
- [`cantools`](https://github.com/eerimoq/cantools)
- GCC or MinGW (for Windows)

## 🧹 Cleaning Up
All generated files are stored in the `temp/` directory and are automatically cleaned after testing.

## 📁 Project structure
```graphql
├── dbc/                     # DBC files
├── generate_functions/      # Scripts for generating libraries
├── img/                     # Organization logo
├── temp/                    # Temporary files (auto-cleaned)
├── test_apps/               # Test applications
├── main.py                  # DBC to code generator
├── requirements.txt
└── README.md
```

## 📝 License
This project is licensed under the <b>MIT Licence</b>

## 📫 Contact
For issues or questions, open [issue on GitHub](https://github.com/mobility-lab-vsb/can-library-generator/issues).