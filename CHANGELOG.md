# Changelog

## Unreleased

- Reworked GUI into resizable workspace panels, with database metadata, aligned tables, automatic node width and rounded application icons for all platforms.
- Fixed signed decoding, Motorola bit order and packing of signals wider than 32 bits in C and C++.
- Added exact 64-bit raw packaging and validation before packaging.
- Unified C/C++ counter, CRC and callback generation, including J1939 protection hooks.
- Fixed RX/TX selection independence and database-aware message selection.
- Added explicit validation for unsupported multiplexing, floating-point wire signals, payload lengths and conflicting generated identifiers.
- Removed dynamic vectors from embedded C++ registries and signal lists; exposed the registry count in both C++ modes.
- Split GUI, selection and export services; made headless generators select the bundled database dynamically.
- Added native codec and protection regression tests, strict compiler checks and CI coverage across all branches and three operating systems.
- Unified runtime dependencies, restored Python wheel packaging and centralized version injection.
- Gated development/release builds on tests and release publication on successful builds for all platforms.
- Updated README, integration guide and generated API documentation.

## v4.8.1

- Initialized unused J1939 payload bytes to `0xFF` during generation and packaging.
- Fixed TX selection for messages with multiple transmitters.
- Improved generated library formatting.

## v1.0.0

- First public release of CAN Library Generator.
- PyQt6 GUI with DBC to C/C++ code generation.
