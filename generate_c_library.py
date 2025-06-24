from collections import defaultdict

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
    h_code = f"// Generated C library header for {library_name}\n\n"
    h_code += f"#ifndef {library_name.upper()}_H\n"
    h_code += f"#define {library_name.upper()}_H\n\n"
    h_code += "#include <stdint.h>\n"
    h_code += "#include <string.h>\n"
    h_code += "#include <stdio.h>\n"
    h_code += "#include <stddef.h>\n\n"

    # Define the DBCSignal structure
    h_code += "// Structure for signal\n"
    h_code += "typedef struct {\n"
    h_code += "    const char *name;\n"
    h_code += "    int startBit;\n"
    h_code += "    int length;\n"
    h_code += "    const char *byteOrder;\n"
    h_code += "    char valueType;\n"
    h_code += "    double factor;\n"
    h_code += "    double offset;\n"
    h_code += "    double min;\n"
    h_code += "    double max;\n"
    h_code += "    const char *unit;\n"
    h_code += "    const char *receiver;\n"
    h_code += "    uint32_t raw_value;\n"
    h_code += "    double value;\n"
    h_code += "} DBCSignal;\n\n"

    # Base message structure
    h_code += "// Base message structure\n"
    h_code += "typedef struct {\n"
    h_code += "    uint32_t id;\n"
    h_code += "    const char *name;\n"
    h_code += "    uint8_t dlc;\n"
    h_code += "    const char *sender;\n"
    h_code += "    size_t num_signals;\n"
    h_code += "    DBCSignal *signals;\n"
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
        h_code += f"// Message: {message_name}\n"
        h_code += f"typedef struct {{\n"
        h_code += "    DBCMessageBase base;\n"

        # Add direct signal pointers
        for signal in message.signals:
            if not signal_names or signal.name in signal_names:
                h_code += f"    DBCSignal *{signal.name};\n"

        h_code += f"}} {struct_name};\n\n"

    # Declare messages as extern
    h_code += "// Message declarations\n"
    for message_name in selected_messages:
        struct_name = f"DBCMessage_{message_name.replace(' ', '')}"
        h_code += f"extern {struct_name} {message_name};\n"

    # Message registry
    h_code += "\n// Message registry\n"
    h_code += "extern DBCMessageBase* const dbc_all_messages[];\n"
    h_code += "extern const size_t dbc_all_messages_count;\n\n"

    # Function
    h_code += "// Functions\n"
    h_code += "DBCMessageBase* dbc_find_message_by_id(uint32_t can_id);\n"
    h_code += "uint32_t dbc_parse_signal(const uint8_t* data, uint16_t startBit, uint8_t length, const char* byteOrder);\n"
    h_code += "int dbc_decode_message(uint32_t can_id, uint8_t dlc, const uint8_t* data);\n\n"

    h_code += f"#endif // {library_name.upper()}_H\n"

    # Generate C implementation file (.c)
    c_code = f"// Generated C library implementation for {library_name}\n\n"
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
    c_code += """// Find message by CAN ID
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

    # Decode message function
    c_code += """// Decode CAN message
int dbc_decode_message(uint32_t can_id, uint8_t dlc, const uint8_t* data) {
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
    return h_code, c_code