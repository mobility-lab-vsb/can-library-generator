# Integration guide

The API reference is generated from the bundled example DBC in C and C++. Each language has a separate reference. Names depend on the selected database and library prefix. The examples below use `cangen`.

## Message and signal storage

`cangen_db.h` (or `.hpp`) declares message objects, signal objects and the message registry. `cangen_all_messages_count` gives its size. C uses fixed arrays. Desktop C++ uses vectors; embedded C++ uses fixed arrays. Do not use vector-specific operations in code intended for both C++ modes.

Each signal exposes an unsigned `raw_value` containing its wire bits and a `phys_value` containing the scaled value. Signed wire values are sign-extended before scale and offset are applied. `raw_value` preserves the two's-complement bit pattern.

Generated initial payloads contain zero for ordinary CAN messages and `0xFF` for J1939 messages. `<prefix>_init(msg)` restores signal initial values and invokes the optional initialization callback; package the message when you need those values encoded in the payload.

## Encoding and decoding

```c
#include "cangen_interface.h"

int receive(uint32_t id, const uint8_t *bytes, uint8_t length)
{
    return cangen_unpackage_message(id, bytes, length);
}
```

Lengths are bytes, not encoded CAN DLC values. Unpack rejects a null data pointer, an unknown ID or a different payload length. It updates both raw and physical signal values. Package rejects invalid/non-finite physical values before changing the payload. Values are rounded to the nearest representable raw integer, with halfway cases rounded away from zero.

`cangen_package_message_raw(id)` encodes `raw_value` directly. Use it when every bit of a 64-bit integer must be retained. The physical API uses floating-point values and cannot represent every 64-bit integer exactly. Raw packaging rejects values exceeding the signal width.

Both packaging paths reset unused bits to the database-specific fill value before inserting selected signals. They support Motorola and Intel integer signals up to 64 bits. Invalid bit layouts are rejected during generation; low-level insertion ignores invalid layouts without modifying the supplied buffer.

## Application hooks

Message-specific `<prefix>_<message>_output_processing()` updates enabled counters, calls the optional TX callback, packages the message and applies enabled CRC processing. It prepares the message's `base.data` for transmission; no transport function is declared or called by the generated library. Connect sending manually using your external transport library.

`<prefix>_<message>_input_processing(msg)` decodes a matching message and invokes its RX callback only after successful decoding. Generated signal/message state is mutable; synchronize concurrent access in the application.

J1939 CRC/counter helpers are declared only when selected TX messages need them. Provide implementations in a separate application file. The ordinary `calculate_crc` declaration is supplied by your external library header; include that header when compiling the generated interface source:

- Ordinary CRC: `uint8_t calculate_crc(const uint8_t *data, uint8_t length, uint8_t initial)`; length is the payload byte count. Ordinary configured CRC signals must occupy the first byte.
- J1939 counters: `j1939_increment_ctr_a`, `_d` or `_f`, each accepting the previous counter and returning the next value.
- J1939 checksums: `j1939_calculate_crc_a`, `_c`, `_d` or `_e`, each accepting the message and its current counter. Rules A/D replace byte 7; C/E replace its upper nibble.

These algorithms depend on your database and vehicle specification. The generator does not implement them and does not validate received CRCs or counter sequences. Their associated signals are included automatically when processing is enabled. Counter and checksum fields used by J1939 hooks must be unscaled unsigned integers in the expected layout.

## Compatibility and limits

Compile C with C99 or newer and C++ with C++11 or newer. Some toolchains require `-lm` for rounding functions. Use definitions generated for the same language and generation options. Regenerate dependent libraries when upgrading because the embedded C++ registry and raw insertion signatures have changed.

Supported payload sizes are 0-8 bytes for classic CAN and 12, 16, 20, 24, 32, 48 or 64 bytes for CAN FD. Multiplexed messages, IEEE floating-point wire signals and J1939 transport-protocol payloads are not supported and fail generation explicitly.

Selected databases must not produce duplicate message identifiers or symbols. Signal names are sanitized; collisions after sanitization are rejected. Library prefixes and message names must be valid C/C++ identifiers and cannot be reserved keywords. Selection uses the database and frame identity, allowing one of several identically named database messages to be selected safely.

Generated files are replaced on regeneration. Keep hooks and integration code outside them. See the repository README for GUI options, tests and build commands.
