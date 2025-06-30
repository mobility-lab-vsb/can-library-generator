from collections import defaultdict

def generate_cpp_code(selected_items, library_name, dbs, tree):
    """Generate C++ code for selected messages and signals."""
    # Group selected messages and signals
    selected_messages = defaultdict(list)  # Dictionary to store selected messages and their signals
    for item in selected_items:
        item_type = tree.item(item, "values")[0]
        if item_type == "Message":
            message_name = tree.item(item, "text")
            selected_messages[message_name] = []  # Select all signals if the message is selected
        elif item_type == "Signal":
            parent = tree.parent(item)
            message_name = tree.item(parent, "text")
            signal_name = tree.item(item, "text")
            selected_messages[message_name].append(signal_name)

    # ---------- .hpp file ----------

    # Generate C++ header file (.hpp)
    hpp_code = f"// Generated C++ library header for {library_name}\n\n"
    hpp_code += f"#ifndef {library_name.upper()}_HPP\n"
    hpp_code += f"#define {library_name.upper()}_HPP\n\n"
    hpp_code += "#include <cstring>\n"
    hpp_code += "#include <vector>\n"
    hpp_code += "#include <cstdint>\n"
    hpp_code += "#include <iostream>\n\n"

    # Define the DBCSignal structure
    hpp_code += "// Structure for signal\n"
    hpp_code += "struct DBCSignal {\n"
    hpp_code += "    std::string name;\n"
    hpp_code += "    int startBit;\n"
    hpp_code += "    int length;\n"
    hpp_code += "    std::string byteOrder;\n"
    hpp_code += "    char valueType;\n"
    hpp_code += "    double factor;\n"
    hpp_code += "    double offset;\n"
    hpp_code += "    double min;\n"
    hpp_code += "    double max;\n"
    hpp_code += "    std::string unit;\n"
    hpp_code += "    std::string receiver;\n"
    hpp_code += "    uint32_t raw_value = 0;\n"
    hpp_code += "    double value = 0.0;\n"
    hpp_code += "\n"
    hpp_code += "    // Constructor\n"
    hpp_code += "    DBCSignal(std::string n, int start, int len, std::string byteOrder, char valueType, "
    hpp_code += "double factor, double offset, double min = 0.0, double max = 0.0, "
    hpp_code += "std::string unit = \"\", std::string receiver = \"\")\n"
    hpp_code += "        : name(n), startBit(start), length(len), byteOrder(byteOrder), valueType(valueType), "
    hpp_code += "factor(factor), offset(offset), min(min), max(max), unit(unit), receiver(receiver), raw_value(0), value(0.0) {}\n"
    hpp_code += "};\n\n"

    # Define the DBCMessageBase structure
    hpp_code += "// Structure for message\n"
    hpp_code += "struct DBCMessageBase {\n"
    hpp_code += "    int id;\n"
    hpp_code += "    std::string name;\n"
    hpp_code += "    int dlc;\n"
    hpp_code += "    std::string sender;\n"
    hpp_code += "    std::vector<DBCSignal*> signals;\n"
    hpp_code += "};\n\n"

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
        hpp_code += f"// Message {message_name}\n"
        hpp_code += f"struct {struct_name} {{\n"
        hpp_code += "    DBCMessageBase base;\n"

        # Add direct signal pointers
        for signal in message.signals:
            if not signal_names or signal.name in signal_names:
                hpp_code += f"    DBCSignal *{signal.name};\n"

        hpp_code += "};\n\n"

    # Declare messages in the header file as extern
    hpp_code += "// Message declaration\n"
    for message_name in selected_messages:
        struct_name = f"DBCMessage_{message_name.replace(' ', '')}"
        hpp_code += f"extern {struct_name} {message_name};\n"

    # Message registry
    hpp_code += "\n// Message registry\n"
    hpp_code += "extern std::vector<DBCMessageBase*> dbc_all_messages;\n\n"

    # Function
    hpp_code += "// Functions\n"
    hpp_code += "DBCMessageBase* dbc_find_message_by_id(uint32_t can_id);\n"
    hpp_code += "uint32_t dbc_parse_signal(const uint8_t* data, uint16_t startBit, uint8_t length, std::string byteOrder);\n"
    hpp_code += "bool dbc_unpackage_message(uint32_t can_id, uint8_t dlc, const uint8_t* data);\n"

    hpp_code += f"\n#endif // {library_name.upper()}_HPP\n"

    # ---------- .cpp file ----------

    # Generate C++ implementation file (.cpp)
    cpp_code = f"// Generated C++ library implementation for {library_name}\n\n"
    cpp_code += f'#include "{library_name}.hpp"\n\n'

    # Define messages in the implementation file
    cpp_code += "// ---------------- Signal definitions ----------------\n\n"

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
            continue  # Skip if the message is not found

        cpp_code += f"// {message_name} signals\n"
        for signal in message.signals:
            if not signal_names or signal.name in signal_names:  # Add only selected signals
                min_value = signal.minimum if signal.minimum is not None else 0.0
                max_value = signal.maximum if signal.maximum is not None else 0.0

                cpp_code += (
                    f"static DBCSignal {signal.name}(\"{signal.name}\", {signal.start}, {signal.length}, \"{'big_endian' if signal.byte_order == 'big_endian' else 'little_endian'}\","
                    f"'{'s' if signal.is_signed else 'u'}', {signal.scale}, {signal.offset}, {min_value}, {max_value}, \"{signal.unit}\", "
                    f"\"{', '.join(signal.receivers) if signal.receivers else 'None'}\");\n")

        cpp_code += "// ---------------- Message definitions ----------------\n\n"

        struct_name = f"DBCMessage_{message_name.replace(' ', '')}"
        cpp_code += f"// Message {message_name}\n"

        cpp_code += f"{struct_name} {message.name} = {{\n"
        cpp_code += "    {\n"
        cpp_code += f"        {message.frame_id},\n"
        cpp_code += f"        \"{message.name}\",\n"
        cpp_code += f"        {message.length},\n"
        cpp_code += f"        \"{message.senders[0] if message.senders else ''}\",\n"
        cpp_code += "        {\n"

        for signal in message.signals:
            cpp_code += f"            &{signal.name},\n"

        cpp_code += "        }\n"
        cpp_code += "    },\n"

        for signal in message.signals:
            cpp_code += f"    &{signal.name},\n"

        cpp_code += "};\n\n"

    # Message registry
    cpp_code += "// ---------------- Message registry ----------------\n\n"
    cpp_code += "std::vector<DBCMessageBase*> dbc_all_messages = {\n"
    for message_name in selected_messages:
        cpp_code += f"    &{message_name}.base,\n"
    cpp_code += "};\n\n"

    # Functions
    cpp_code += "// ---------------- Functions ----------------\n\n"
    # Find message by ID function
    cpp_code += """// Find message by CAN ID
DBCMessageBase* dbc_find_message_by_id(uint32_t can_id) {
    for (auto* msg : dbc_all_messages) {
        if (msg->id == static_cast<int>(can_id)) {
            return msg;
        }
    }
    return nullptr;
}\n\n"""

    # Parse signal function
    cpp_code += """// Parse signal function
uint32_t dbc_parse_signal(const uint8_t* data, uint16_t startBit, uint8_t length, std::string byteOrder) {
    uint64_t raw = 0;

    for (int i = 0; i < 8; ++i) {
        raw |= (static_cast<uint64_t>(data[i]) << (i * 8));
    }

    if (strcmp(byteOrder, "little_endian") == 0) {
        return static_cast<uint32_t>((raw >> startBit) & ((1ULL << length) - 1));
    }
    else {
        // Big endian bit parsing – adjust for your actual use
        uint64_t result = 0;
        for (int i = 0; i < length; ++i) {
            int src_bit = startBit + i;
            int byte_index = 7 - (src_bit / 8);
            int bit_index = src_bit % 8;
            int bit_value = (data[byte_index] >> bit_index) & 0x1;
            result |= (bit_value << (length - 1 - i));
        }
        return static_cast<uint32_t>(result);
    }
}\n\n"""

    # Unpackage message function
    cpp_code += """// Unpackage CAN message
bool dbc_unpackage_message(uint32_t can_id, uint8_t dlc, const uint8_t* data) {
    DBCMessageBase* msg = dbc_find_message_by_id(can_id);
    if (!msg || msg->dlc != dlc) {
        std::cout << "Message not found or DLC mismatch!" << std::endl;
        return false;
    }
    std::cout << "Message found!" << std::endl;

    for (DBCSignal* sig : msg->signals) {
        uint32_t raw = dbc_parse_signal(data, sig->startBit, sig->length, sig->byteOrder.c_str());
        sig->raw_value = raw;
        if (sig->valueType == 's') {
            int64_t signed_val = static_cast<int64_t>(raw);
            int shift = 64 - sig->length;
            signed_val = (signed_val << shift) >> shift;  // sign-extend
            sig->value = signed_val * sig->factor + sig->offset;
        }
        else {
            sig->value = raw * sig->factor + sig->offset;
        }
    }

    return true;
}"""

    return hpp_code, cpp_code