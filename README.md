# CAN Library Generator

Desktop application for generating C and C++ CAN libraries from DBC databases.

## Installation

Download a Windows, macOS or Linux package from [Releases](https://github.com/mobility-lab-vsb/can-library-generator/releases).

For development, use Python 3.11 or newer (CI tests 3.11 and 3.12):

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m canlibrarygenerator
```

For application use without development tools, install `requirements.txt` instead. The installed `can-library-generator` command also opens the application. From the repository, `python -m src.canlibrarygenerator` remains supported.

## Selecting a library

1. Select one or more DBC files. The header shows the database protocol and version when available.
2. Select RX and TX nodes, or choose individual messages and signals. A message with multiple transmitters is selected when any selected TX node transmits it.
3. Resize the Nodes and Messages & Signals panels as needed. The initial Nodes width fits the longest name. The Settings button shows or hides generation settings.
4. Enter a C/C++ identifier as the library prefix, choose the language and options, then select Generate Library and an output directory.

Generation settings:

| Option | Effect |
| --- | --- |
| Generate can_db_def header | Include the shared message/signal type definitions. Disable only when compatible definitions already exist in your project. |
| Embedded library | Use fixed arrays, including in C++, rather than the desktop C++ vectors. |
| Signal names with units | Append sanitized units to generated signal identifiers. |
| Message counter processing | Update configured counters during TX processing. |
| CRC processing | Call the application's configured checksum hooks during TX processing. |
| Message callbacks | Include callbacks for initialization, RX and TX processing. |

RX and TX selections are independent. Clearing RX while TX remains enabled keeps the message's signals selected. Selecting only some signals leaves other bits at their default fill value.

## Generated files

```text
<prefix>/
  inc/
    can_db_def.h
    <prefix>_db.h
    <prefix>_interface.h
  src/
    <prefix>_db.c
    <prefix>_interface.c
```

C++ uses `.hpp` and `.cpp` extensions. Files are UTF-8. Regeneration replaces generated files; keep application hooks in separate files. Regenerate the shared definitions and dependent libraries together when changing language, embedded mode or callback options.

The codec supports signed and unsigned integer signals of 1-64 bits, Intel and Motorola byte order, scale and offset, classic CAN and CAN FD payloads. CAN FD lengths must be one of 12, 16, 20, 24, 32, 48 or 64 bytes; classic payloads use 0-8 bytes. J1939 unused data bytes are initialized and packaged as `0xFF`; other messages use zero.

Multiplexed messages, IEEE floating-point wire signals and J1939 transport-protocol payloads are currently rejected with an explanation. Duplicate selected message names or CAN IDs across databases, invalid identifiers and colliding generated signal names are also rejected. You can select a single message from databases containing the same name.

## Integration

Compile both generated source files and add `inc/` to your include path. C compilation requires C99 or newer; C++ requires C++11 or newer. On toolchains that require it, link the math library (`-lm`).

Set a signal's `phys_value` and call `<prefix>_package_message(id)`, which checks values before writing the payload. For exact 64-bit integer payloads, set `raw_value` and call `<prefix>_package_message_raw(id)`: the physical API uses floating-point values and cannot represent every 64-bit integer exactly. Both packaging functions return zero on success and `-1` on error.

Use `<prefix>_unpackage_message(id, data, length)` to decode received bytes. Message-specific RX functions also run callbacks; message-specific TX functions update counters, run callbacks, package and calculate CRC. Connect the prepared message to your transport library manually; the generator does not declare or call a send function.

Implement the counter and checksum hooks declared in your generated interface header. The generator supplies their call sites, not the vehicle-specific algorithms. RX processing decodes signals; it does not validate CRC or counter sequences. See the [integration guide](docs/guide.md) and [generated API reference](docs/index.html).

## Tests

Install `requirements-dev.txt` and ensure `gcc` and `g++` are available on PATH (MinGW/UCRT64 on Windows).

```sh
python -m unittest discover -s src/canlibrarygenerator/test -p "test_*.py"
python -m src.canlibrarygenerator.test.test_pipeline
python -m build --wheel
python -m src.canlibrarygenerator.scripts.check_wheel
```

For headless GUI tests set `QT_QPA_PLATFORM=offscreen`. The tests compare codec results against cantools, compile generated C/C++ with warnings treated as errors, exercise J1939 protection hooks, and check GUI selections and layout. The native pipeline checks six combinations of language, embedded mode and unit suffixes. Generated test files use isolated temporary directories and are cleaned automatically.

CI runs checks for every branch and pull request on Windows, Linux and macOS. Development package builds on `dev` and `development/**` wait for checks. A `v*` tag runs checks, builds all three OS packages, then publishes a release only after all builds succeed.

## Documentation and packaging

With Doxygen available on PATH:

```sh
python -m src.canlibrarygenerator.scripts.build_docs
```

This rebuilds `docs/api/` from current templates and the bundled example database. Manual documentation lives in `docs/guide.md`. The documentation workflow runs the same command.

For native packaging, install the build dependencies, set the version, then use Briefcase:

```sh
python -m src.canlibrarygenerator.scripts.inject_version v4.8.1
briefcase create
briefcase build
briefcase package
```

Windows CI additionally renders `installer.iss.in` using `python -m src.canlibrarygenerator.scripts.make_installer` and builds it with Inno Setup. Version injection updates the central Python version and Briefcase's numeric package version. Untagged source builds use `0.0.0.dev0`.

## Project structure

- `ui/`: window, selection widgets/controller and theme.
- `selection.py`, `service.py`: database-aware selection and loading/export without Qt.
- `ir/`: validation and the intermediate representation.
- `renderers/`, `templates/`: C/C++ rendering and shared codec/processing templates.
- `scripts/`: packaging, documentation and version tools.
- `test/`: GUI, validation and native codec regression tests.

## License and support

MIT license; see [LICENSE](LICENSE). Report problems through [GitHub issues](https://github.com/mobility-lab-vsb/can-library-generator/issues).
