# DBC to C Library Generator

This project is a Python tool that parses DBC (CAN database) files and generates a C library for handling messages and signals.

## Features

- Parses DBC files using the `cantools` library.
- Generates structured C code with message and signal definitions.
- Ensures correct syntax and type safety.

## Installation

### Clone the repository

```sh
git clone <repository-url>
cd <repository-name>
```

## Install dependencies

```sh
pip install -r requirements.txt
```

## Usage

Run the script
```sh
python main.py
```
The generated C library will be stored in the selected directory

## Generated Files
The scriptgenerates the foloving C files:

- name_of_your_library.h - Header file with message and signal definitions
- name_of_your_library.c - Source file implementing parsing and struct handling

## License
This project is licensed inder the <b>MIT Licence</b>