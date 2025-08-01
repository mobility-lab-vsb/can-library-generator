from collections import defaultdict
from datetime import datetime

def _generate_file_header_comment(file_name, brief_description):
    """Generates the Doxygen header comment."""
    current_date = datetime.now().strftime("%d.%m.%Y")
    current_year = datetime.now().year

    comment = f"""/*******************************************************************************
*
* @file         {file_name}
* @brief        {brief_description}
* @author       Generated using CAN Library Generator tool
* @date         {current_date}
*
* @copyright    (c) {current_year} Mobility Lab, VŠB - Technical University of Ostrava
* All rights reserved.
*
* @details      This file was automatically generated by CAN Library Generator tool.
* Contains definitions and/or implementations of functions for working with CAN messages.
* Any manual modifications in this file will be overwritten
* during subsequent generation.
*
******************************************************************************/

/**
 * @file {file_name}
 * @brief Defines the core structures and functions for CAN communication.
 */
\n"""
    return comment

def _generate_function_doxygen_comment(function_name, params, return_type, brief="", details=""):
    """Generates a Doxygen comment block for a function."""
    comment = f"/**\n * @brief {brief}\n *\n"
    for param_name, param_desc in params:
        comment += f" * @param {param_name} {param_desc}\n"
    if return_type and return_type != "void":
        comment += f" * @return {return_type} {details}\n"
    elif details:
        comment += f" * @details {details}\n"
    comment += f" */\n"
    return comment

def generate_c_code(selected_items, library_name, dbs, tree):
    """Generate C code for selected messages and signals."""
    # Group selected messages and signals
    selected_messages = defaultdict(list)
    for item in selected_items:
        item_type = tree.item(item, "values")[0]
        if item_type == "Message":
            message_name = tree.item(item, "text")
            selected_messages[message_name] = []
        elif item_type == "Signal":
            parent = tree.parent(item)
            message_name = tree.item(parent, "text")
            signal_name = tree.item(item, "text")
            selected_messages[message_name].append(signal_name)

    # Generate C header file (.h)
    h_code = _generate_file_header_comment(f"{library_name}.h", "Definitions of structures and functions for CAN communication")
    h_code += f"#ifndef {library_name.upper()}_H\n"
    h_code += f"#define {library_name.upper()}_H\n\n"
    h_code += "#include <stdint.h>\n"
    h_code += "#include <string.h>\n"
    h_code += "#include <stdio.h>\n"
    h_code += "#include <stddef.h>\n\n"

    # Define the DBCSignal structure
    h_code += "/**\n * @brief   Structure for signal representation.\n */\n"
    h_code += "typedef struct {\n"
    h_code += "    const char *name; /**< Name of the signal. */\n"
    h_code += "    int startBit;     /**< Start bit of the signal. */\n"
    h_code += "    int length;       /**< Length of the signal in bits. */\n"
    h_code += "    const char *byteOrder; /**< Byte order (little_endian/big_endian). */\n"
    h_code += "    char valueType;   /**< Value type ('s' for signed, 'u' for unsigned). */\n"
    h_code += "    double factor;    /**< Factor for conversion to physical value. */\n"
    h_code += "    double offset;    /**< Offset for conversion to physical value. */\n"
    h_code += "    double min;       /**< Minimum physical value. */\n"
    h_code += "    double max;       /**< Maximum physical value. */\n"
    h_code += "    const char *unit; /**< Unit of the signal. */\n"
    h_code += "    const char *receiver; /**< Receiver of the signal. */\n"
    h_code += "    uint32_t raw_value; /**< Current raw value of the signal. */\n"
    h_code += "    double value;     /**< Current physical value of the signal. */\n"
    h_code += "} DBCSignal;\n\n"

    # Base message structure
    h_code += "/**\n * @brief   Base structure for CAN message.\n */\n"
    h_code += "typedef struct {\n"
    h_code += "    uint32_t id;      /**< CAN ID of the message. */\n"
    h_code += "    const char *name; /**< Name of the message. */\n"
    h_code += "    uint8_t dlc;      /**< Data Length Code (DLC) of the message. */\n"
    h_code += "    const char *sender; /**< Sender of the message. */\n"
    h_code += "    size_t num_signals; /**< Number of signals in the message. */\n"
    h_code += "    DBCSignal *signals; /**< Pointer to the array of the message signals. */\n"
    h_code += "} DBCMessageBase;\n\n"

    # Generate unique struct for each message
    for message_name, signal_names in selected_messages.items():
        message = None
        for db in dbs:
            try:
                message = db.get_message_by_name(message_name)
                break
            except KeyError:
                continue
        if not message:
            continue

        struct_name = f"DBCMessage_{message_name.replace(' ', '')}"
        h_code += f"// Structure for CAN message {message_name}.\n\n"
        h_code += f"typedef struct {{\n"
        h_code += "    DBCMessageBase base;\n"

        # Add direct signal pointers
        for signal in message.signals:
            if not signal_names or signal.name in signal_names:
                h_code += f"    DBCSignal *{signal.name};\n"

        h_code += f"}} {struct_name};\n\n"

    # Declare messages as extern
    h_code += "// Declaration of global CAN message instances.\n"
    for message_name in selected_messages:
        struct_name = f"DBCMessage_{message_name.replace(' ', '')}"
        h_code += f"extern {struct_name} {message_name};\n"

    # Message registry
    h_code += "// Global registry of all defined CAN messages.\n"
    h_code += "extern DBCMessageBase* const dbc_all_messages[];\n"
    h_code += "// Number of messages in the dbc_all_messages registry.\n"
    h_code += "extern const size_t dbc_all_messages_count;\n\n"

    # Function declarations with Doxygen comments
    h_code += _generate_function_doxygen_comment(
        "dbc_find_message_by_id",
        [("can_id", "The CAN ID of the message to find.")],
        "DBCMessageBase*",
        brief="Finds a CAN message in the registry by its ID.",
        details="Returns a pointer to the found message or NULL if the message was not found."
    )
    h_code += "DBCMessageBase* dbc_find_message_by_id(uint32_t can_id);\n"

    h_code += _generate_function_doxygen_comment(
        "dbc_parse_signal",
        [("data", "Pointer to the array of CAN data bytes."),
         ("startBit", "Start bit of the signal."),
         ("length", "Length of the signal in bits."),
         ("byteOrder", "String specifying byte order (\"little_endian\" or \"big_endian\").")],
        "uint32_t",
        brief="Parses the raw signal value from CAN data.",
        details="Extracts signal bits from the data array according to the specified start bit, length and byte order."
    )
    h_code += "uint32_t dbc_parse_signal(const uint8_t* data, uint16_t startBit, uint8_t length, const char* byteOrder);\n"

    h_code += _generate_function_doxygen_comment(
        "dbc_unpackage_message",
        [("can_id", "CAN ID of the received message."),
         ("dlc", "Data Length Code (DLC) of the received message."),
         ("data", "Pointer to the array of received CAN data bytes.")],
        "int",
        brief="Unpackages a received CAN message and updates signal values.",
        details="Finds the message by ID, checks DLC, parses raw signal values, and converts them to physical values. Returns 0 on success, -1 on error (message not found or DLC mismatch)."
    )
    h_code += "int dbc_unpackage_message(uint32_t can_id, uint8_t dlc, const uint8_t* data);\n"

    h_code += _generate_function_doxygen_comment(
        "dbc_insert_signal",
        [("data", "Pointer to the byte array where the signal should be inserted."),
         ("raw_value", "Raw signal value to insert."),
         ("start_bit", "Start bit of the signal."),
         ("length", "Length of the signal in bits."),
         ("byteOrder", "String specifying byte order (\"little_endian\" or \"big_endian\").")],
        "void",
        brief="Inserts the raw signal value into a CAN data byte array.",
        details="Writes the bits of the raw signal value into the data array according to the specified start bit, length, and byte order."
    )
    h_code += "void dbc_insert_signal(uint8_t* data, uint32_t raw_value, int start_bit, int length, const char* byteOrder);\n"

    h_code += _generate_function_doxygen_comment(
        "dbc_package_message",
        [("can_id", "CAN ID of the message to package."),
         ("dlc", "Data Length Code (DLC) of the message to package."),
         ("data", "Pointer to the byte array where message signals should be packaged.")],
        "int",
        brief="Packages CAN message signals into a data array for transmission.",
        details="Finds the message by ID, checks DLC, and inserts raw signal values into the data array. Returns 0 on success, -1 on error."
    )
    h_code += "int dbc_package_message(uint32_t can_id, uint8_t dlc, const uint8_t* data);\n\n"

    h_code += f"#endif // {library_name.upper()}_H\n"

    # Generate C implementation file (.c)
    c_code = _generate_file_header_comment(f"{library_name}.c", "Implementation of functions for CAN communication")
    c_code += f'#include "{library_name}.h"\n\n'

    # Define messages and signals
    message_definitions = []
    for message_name, signal_names in selected_messages.items():
        # Find the message in the loaded databases
        message = None
        for db in dbs:
            try:
                message = db.get_message_by_name(message_name)
                break
            except KeyError:
                continue
        if not message:
            continue # Skip if the message is not found

        struct_name = f"DBCMessage_{message_name.replace(' ', '')}"
        c_code += f"// Message: {message.name}\n"

        # Define signals array
        if message.signals:
            c_code += f"static DBCSignal {message.name}_signals[] = {{\n"
            for signal in message.signals:
                if not signal_names or signal.name in signal_names:
                    min_value = signal.minimum if signal.minimum is not None else 0.0
                    max_value = signal.maximum if signal.maximum is not None else 0.0
                    unit_value = f"\"{signal.unit}\"" if signal.unit else "\"\""
                    receiver_value = f"\"{', '.join(signal.receivers)}\"" if signal.receivers else "\"\""

                    c_code += "    {\n"
                    c_code += f"        .name = \"{signal.name}\",\n"
                    c_code += f"        .startBit = {signal.start},\n"
                    c_code += f"        .length = {signal.length},\n"
                    c_code += f"        .byteOrder = \"{'big_endian' if signal.byte_order == 'big_endian' else 'little_endian'}\",\n"
                    c_code += f"        .valueType = '{'s' if signal.is_signed else 'u'}',\n"
                    c_code += f"        .factor = {signal.scale},\n"
                    c_code += f"        .offset = {signal.offset},\n"
                    c_code += f"        .min = {min_value},\n"
                    c_code += f"        .max = {max_value},\n"
                    c_code += f"        .unit = {unit_value},\n"
                    c_code += f"        .receiver = {receiver_value},\n"
                    c_code += f"        .raw_value = 0\n"
                    c_code += "    },\n"
            c_code += "};\n\n"

            num_signals = len([s for s in message.signals if not signal_names or s.name in signal_names])
        else:
            num_signals = 0
            c_code += "// No signals for this message\n"

        # Define message struct
        senders = ', '.join(message.senders)
        sender_value = f"\"{senders}\"" if message.senders else "\"\""
        signals_array = f"{message.name}_signals" if num_signals > 0 else "\"\""

        c_code += f"{struct_name} {message.name} = {{\n"
        c_code += f"    .base = {{\n"
        c_code += f"        .id = {message.frame_id},\n"
        c_code += f"        .name = \"{message.name}\",\n"
        c_code += f"        .dlc = {message.length},\n"
        c_code += f"        .sender = {sender_value},\n"
        c_code += f"        .num_signals = {num_signals},\n"
        c_code += f"        .signals = {signals_array}\n"
        c_code += f"    }},\n"

        # Assign direct pointers to signals
        for i, signal in enumerate(message.signals):
            if not signal_names or signal.name in signal_names:
                c_code += f"    .{signal.name} = &{message.name}_signals[{i}],\n"

        c_code += "};\n\n"
        message_definitions.append(f"(DBCMessageBase*)&{message.name}")

    # Message registry
    c_code += "// Message registry\n"
    c_code += f"DBCMessageBase* const dbc_all_messages[] = {{\n    "
    c_code += ",\n    ".join(message_definitions)
    c_code += "\n};\n\n"
    c_code += f"const size_t dbc_all_messages_count = {len(message_definitions)};\n\n"

    # Find message function
    c_code += """// Find message by ID function
DBCMessageBase* dbc_find_message_by_id(uint32_t can_id) {
    for (size_t i = 0; i < dbc_all_messages_count; i++) {
        if (dbc_all_messages[i]->id == can_id) {
            return dbc_all_messages[i];
        }
    }
    return NULL;
}
\n"""

    # Parse signal function
    c_code +="""// Parse signal function
uint32_t dbc_parse_signal(const uint8_t* data, uint16_t startBit, uint8_t length, const char* byteOrder) {
    uint64_t result = 0;

    if (strcmp(byteOrder, "little_endian") == 0) {
        // Intel (little endian)
        int byteIndex = startBit / 8;
        int bitIndex = startBit % 8;
        int bitsLeft = length;
        int shift = 0;

        while (bitsLeft > 0) {
            uint8_t byte = data[byteIndex];
            int bitsInThisByte = (bitsLeft < (8 - bitIndex)) ? bitsLeft : (8 - bitIndex);
            uint8_t mask = ((1 << bitsInThisByte) - 1) << bitIndex;
            uint8_t bits = (byte & mask) >> bitIndex;
            result |= ((uint64_t)bits << shift);

            bitsLeft -= bitsInThisByte;
            shift += bitsInThisByte;
            byteIndex++;
            bitIndex = 0;
        }

    }
    else {
        // Motorola (big endian)
        for (int i = 0; i < length; i++) {
            int bitPos = startBit - i;
            int byteIndex = bitPos / 8;
            int bitIndex = bitPos % 8;
            uint8_t bit = (data[byteIndex] >> (7 - bitIndex)) & 0x1;
            result = (result << 1) | bit;
        }
    }

    return result;
}
\n"""

    # Unpackage message function
    c_code += """// Unpackage message function
int dbc_unpackage_message(uint32_t can_id, uint8_t dlc, const uint8_t* data) {
    DBCMessageBase* msg = dbc_find_message_by_id(can_id);
    if (!msg || msg->dlc != dlc) {
        printf("Message not found or DLC mismatch!\\n");
        return -1;
    }

    printf("Message found!\\n");

    for (size_t i = 0; i < msg->num_signals; i++) {
        DBCSignal* sig = &msg->signals[i];

        // Parse raw value
        sig->raw_value = dbc_parse_signal(data, sig->startBit, sig->length, sig->byteOrder);

        // Exchange to physical value
        sig->value = (sig->raw_value * sig->factor) + sig->offset;
    }

    return 0;
}
\n"""

    # Insert signal data function
    c_code += """// Insert signal data function
void dbc_insert_signal(uint8_t* data, uint32_t raw_value, int start_bit, int length, const char* byteOrder) {
    if (strcmp(byteOrder, "little_endian") == 0) {
        for (int i = 0; i < length; i++) {
            int bitIndex;
            if (strcmp(byteOrder, "little_endian") == 0) {
                // Intel (little endian)
                bitIndex = start_bit + i;
            }

            else {
                int byteIndex = start_bit / 8;
                int bit_in_byte = 7 - (start_bit % 8);
                int abs_bit = byteIndex * 8 + bit_in_byte;

                int bit_offset = i;
                int current_bit = abs_bit - bit_offset;

                bitIndex = current_bit;
            }

            int byteIndex = bitIndex / 8;
            int bit_in_byte = bitIndex % 8;

            if ((raw_value >> i) & 1) {
                data[byteIndex] |= (1 << bit_in_byte);
            }
            else {
                data[byteIndex] &= ~(1 << bit_in_byte);
            }
        }
    }
}
\n"""

    # Package message function
    c_code += """// Package message function
int dbc_package_message(uint32_t can_id, uint8_t dlc, const uint8_t* data) {
    DBCMessageBase* msg = dbc_find_message_by_id(can_id);
    if (!msg || msg->dlc != dlc) {
        printf("Message not found or DLC mismatch!\\n");
        return -1;
    }

    printf("Message found!\\n");

    for (size_t i = 0; i < msg->num_signals; i++) {
        DBCSignal* sig = &msg->signals[i];

        dbc_insert_signal(data, sig->raw_value, sig->startBit, sig->length, sig->byteOrder);
    }

    return 0;
}
\n"""
    return h_code, c_code