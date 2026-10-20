from .models import LibraryIR, MessageIR, SignalIR
from ..utils.can_utils import get_dlc_from_data_length
from datetime import datetime

import re
import math
from collections import Counter


J1939_CRC_SIGNAL_LAYOUTS = {
    "A": {
        "start_bit": 56,
        "length": 8,
        "byte_order": "little_endian",
    },
    "C": {
        "start_bit": 60,
        "length": 4,
        "byte_order": "little_endian",
    },
    "D": {
        "start_bit": 56,
        "length": 8,
        "byte_order": "little_endian",
    },
    "E": {
        "start_bit": 60,
        "length": 4,
        "byte_order": "little_endian",
    },
}


J1939_COUNTER_SIGNAL_LAYOUTS = {
    "a": {
        "start_bit": 52,
        "length": 4,
        "byte_order": "little_endian",
        "maximum": 15,
        "not_available": None,
    },
    "d": {
        "start_bit": 56,
        "length": 4,
        "byte_order": "little_endian",
        "maximum": 15,
        "not_available": None,
    },
    "f": {
        "start_bit": 56,
        "length": 4,
        "byte_order": "little_endian",
        "maximum": 7,
        "not_available": 15,
    },
}


SUPPORTED_J1939_CRC_COUNTER_COMBINATIONS = {
    "Aa",
    "Cd",
    "Da",
    "Ef",
}


CPP_KEYWORDS = set("alignas alignof and asm auto bitand bitor bool break case catch char class compl concept const constexpr consteval constinit continue co_await co_return co_yield decltype default delete do double dynamic_cast else enum explicit export extern false float for friend goto if inline int long mutable namespace new noexcept not nullptr operator or private protected public register reinterpret_cast requires return short signed sizeof static static_assert static_cast struct switch template this thread_local throw true try typedef typeid typename union unsigned using virtual void volatile wchar_t while xor _Bool _Complex _Imaginary".split())
CPP_KEYWORDS.update("and_eq or_eq xor_eq not_eq const_cast char8_t char16_t char32_t _Alignas _Alignof _Atomic _Generic _Noreturn _Static_assert _Thread_local".split())


def validate_identifier(value: str, role: str):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) or value in CPP_KEYWORDS:
        raise ValueError(f"{role} '{value}' must be a valid C/C++ identifier and cannot be a keyword.")


def _selection_key(tree, item):
    if hasattr(tree, "message_key"):
        key = tree.message_key(item)
        if key is not None:
            return key
    return tree.item(item, "text")


def _validate_generated_symbols(messages, prefix):
    symbols = {f"{prefix}_{name}" for name in (
        "all_messages", "all_messages_count", "find_message_by_id", "parse_signal",
        "unpackage_message", "insert_signal", "package_message", "package_message_raw",
        "init", "next_bit", "mask", "physical_value", "raw_value")}
    macros = set()
    for message in messages:
        generated = [f"{prefix}_{message.name}", f"{prefix}_db_{message.name}_t",
                     f"{message.name}_signals", f"{message.name}_signal_refs"]
        for mode in ("rx", "tx"):
            if getattr(message, f"mode_{mode}"):
                direction = "input" if mode == "rx" else "output"
                generated.append(f"{prefix}_{message.name}_{direction}_processing")
        for symbol in generated:
            if symbol in symbols:
                raise ValueError(f"Message '{message.name}' produces a colliding generated symbol '{symbol}'.")
            symbols.add(symbol)
        macro = f"{prefix}_{message.name}_ID".upper()
        if macro in macros:
            raise ValueError(f"Message '{message.name}' produces a colliding CAN ID macro '{macro}'.")
        macros.add(macro)


def _validate_message(message, db):
    validate_identifier(message.name, "Message name")
    if message.is_multiplexed():
        raise ValueError(f"Message '{message.name}' uses multiplexing, which is not supported.")
    is_fd = _is_can_fd_message(message, db)
    if message.length not in range(0, 9) and (not is_fd or get_dlc_from_data_length(message.length) is None):
        raise ValueError(f"Message '{message.name}' has unsupported payload length {message.length}. Use Classic CAN 0–8 bytes or CAN FD 12/16/20/24/32/48/64 bytes; transport protocols are not supported.")
    for sig in message.signals:
        if sig.is_float:
            raise ValueError(f"Signal '{sig.name}' uses a floating-point wire representation, which is not supported.")
        if not 1 <= sig.length <= 64:
            raise ValueError(f"Signal '{sig.name}' must contain 1–64 bits.")
        if not math.isfinite(sig.scale) or sig.scale == 0 or not math.isfinite(sig.offset):
            raise ValueError(f"Signal '{sig.name}' must have a finite nonzero factor and a finite offset.")


def _sanitize_identifier_part(value: str) -> str:
    value = value.strip()

    replacements = {
        "%": "percent",
        "°": "deg",
        "/": "p",
        "\\": "p",
        "-": "_",
        " ": "_",
        ".": "_",
        "(": "",
        ")": "",
        "[": "",
        "]": "",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"[^0-9a-zA-Z_]", "_", value)
    value = re.sub(r"_+", "_", value)
    value = value.strip("_")

    if value and (value[0].isdigit() or value in CPP_KEYWORDS):
        value = "sig_" + value
    return value


def _make_signal_code_name(signal_name: str, unit: str, with_unit: bool) -> str:
    base = _sanitize_identifier_part(signal_name)

    if not with_unit:
        return base

    unit_suffix = _sanitize_identifier_part(unit or "")

    if not unit_suffix:
        return base

    return f"{base}_{unit_suffix}"


def _get_message_attribute(message, attribute_name: str, default=0):
    """
    Read a message-level DBC attribute and return its raw value.

    Args:
        message: cantools message object.
        attribute_name: Name of the DBC message attribute.
        default: Value returned when the attribute does not exist.

    Returns:
        Value of the DBC attribute or the supplied default value.
    """
    if (
        message.dbc
        and message.dbc.attributes
        and attribute_name in message.dbc.attributes
    ):
        value = message.dbc.attributes[attribute_name].value

        if value is not None:
            return value

    return default


def _get_database_attribute(db, attribute_name: str, default=None):
    if (
        db.dbc
        and db.dbc.attributes
        and attribute_name in db.dbc.attributes
    ):
        value = db.dbc.attributes[attribute_name].value

        if value is not None:
            return value

    if db.dbc:
        definition = (db.dbc.attribute_definitions or {}).get(attribute_name)
        if definition is not None and definition.default_value is not None:
            return definition.default_value
    return default


def _get_message_enum_attribute_name(message, attribute_name: str) -> str | None:
    if not message.dbc:
        return None
    attribute = (message.dbc.attributes or {}).get(attribute_name)
    definition = (message.dbc.attribute_definitions or {}).get(attribute_name)
    if attribute is not None:
        value = attribute.value
        definition = getattr(attribute, "definition", definition)
    elif definition is not None:
        value = definition.default_value
    else:
        return None

    if isinstance(value, str):
        return value

    choices = getattr(definition, "choices", None)

    if choices is None:
        return None

    try:
        index = int(value)

        if isinstance(choices, dict):
            choice = choices.get(index)
            return str(choice) if choice is not None else None

        if isinstance(choices, (list, tuple)):
            if 0 <= index < len(choices):
                return str(choices[index])

    except (TypeError, ValueError, IndexError, KeyError):
        return None

    return None


def _normalize_enum_name(value: str | None) -> str | None:
    """
    Normalize an enum value for reliable comparison.
    """
    if value is None:
        return None

    return (
        value
        .strip()
        .upper()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _normalize_attribute_name(value) -> str | None:
    if value is None:
        return None

    return (
        str(value)
        .strip()
        .upper()
        .replace(" ", "")
        .replace("-", "")
    )


def _is_j1939_message(message, db) -> bool:
    """Recognize J1939 from the message format or database protocol."""
    return (
        _normalize_attribute_name(getattr(message, "protocol", None)) == "J1939"
        or _normalize_attribute_name(
            _get_message_enum_attribute_name(message, "VFrameFormat")
        ) == "J1939PG"
        or _normalize_attribute_name(
            _get_database_attribute(db, "ProtocolType")
        ) == "J1939"
    )


def _is_can_fd_message(message, db) -> bool:
    """
    Determine whether a message uses CAN FD.

    Non-J1939 messages:
        The value provided by cantools message.is_fd is used directly.

    J1939PG messages:
        J1939PgAppearanceOnBus explicitly selects Classic CAN or CAN FD.

        CAN_EXTENDED:
            Always Classic CAN.

        CANFD_EXTENDED:
            Always CAN FD.

        Default, missing or unknown:
            The result is derived from the database-level BusType attribute.

    Supported normalized BusType values:
        CAN:
            Classic CAN.

        CANFD:
            CAN FD.

    If neither the appearance nor BusType provides a valid result,
    cantools message.is_fd is used as the final fallback.
    """
    frame_format = _normalize_attribute_name(
        _get_message_enum_attribute_name(
            message,
            "VFrameFormat"
        )
    )

    # Non-J1939 messages remain fully controlled by cantools.
    if frame_format != "J1939PG":
        return bool(message.is_fd)

    appearance = _normalize_attribute_name(
        _get_message_enum_attribute_name(
            message,
            "J1939PgAppearanceOnBus"
        )
    )

    # Explicit message-level selection has the highest priority.
    if appearance == "CAN_EXTENDED":
        return False

    if appearance == "CANFD_EXTENDED":
        return True

    # Default, missing or unknown appearance falls back to BusType.
    bus_type = _normalize_attribute_name(
        _get_database_attribute(
            db,
            "BusType",
            None
        )
    )

    if bus_type == "CANFD":
        return True

    if bus_type == "CAN":
        return False

    # Final fallback if BusType is missing or unsupported.
    return bool(message.is_fd)


def _parse_j1939_crc_counter_attribute(message):
    """
    Parse and validate the FsJ1939UseCrcAndCounter message attribute.

    Supported combinations:
        Aa, Cd, Da, Ef

    Args:
        message: cantools message object.

    Returns:
        Tuple:
            (crc_type, counter_type)

        If protection is not configured:
            (None, None)

    Raises:
        ValueError: If the attribute value is invalid or unsupported.
    """
    value = _get_message_enum_attribute_name(
        message,
        "FsJ1939UseCrcAndCounter"
    )

    if value is None:
        return None, None

    value = str(value).strip()

    if not value or value.lower() == "default":
        return None, None

    if len(value) != 2:
        raise ValueError(
            f"Message '{message.name}' has invalid "
            f"FsJ1939UseCrcAndCounter value '{value}'. "
            f"Expected a two-character value such as 'Aa', 'Cd', "
            f"'Da' or 'Ef'."
        )

    crc_type = value[0]
    counter_type = value[1]

    if value not in SUPPORTED_J1939_CRC_COUNTER_COMBINATIONS:
        supported = ", ".join(
            sorted(SUPPORTED_J1939_CRC_COUNTER_COMBINATIONS)
        )

        raise ValueError(
            f"Message '{message.name}' uses unsupported J1939 "
            f"CRC/counter combination '{value}'. "
            f"Supported combinations are: {supported}."
        )

    return crc_type, counter_type


def _find_dbc_signal_by_layout(
    message,
    role: str,
    start_bit: int,
    length: int,
    byte_order: str
):
    """
    Find a DBC signal by its exact bit layout.

    Args:
        message: cantools message object.
        role: Human-readable signal role for error messages.
        start_bit: Expected signal start bit.
        length: Expected signal length in bits.
        byte_order: Expected signal byte order.

    Returns:
        Matching cantools Signal object.

    Raises:
        ValueError: If no signal or multiple signals match.
    """
    matches = [
        signal
        for signal in message.signals
        if signal.start == start_bit
        and signal.length == length
        and signal.byte_order == byte_order
    ]

    if not matches:
        raise ValueError(
            f"Message '{message.name}' uses J1939 protection, "
            f"but its {role} signal was not found. "
            f"Expected start bit {start_bit}, length {length} "
            f"and byte order '{byte_order}'."
        )

    if len(matches) > 1:
        names = ", ".join(signal.name for signal in matches)

        raise ValueError(
            f"Message '{message.name}' contains multiple signals "
            f"matching the {role} layout: {names}."
        )

    return matches[0]


def _find_j1939_protection_signals(
    message,
    crc_type: str,
    counter_type: str
):
    """
    Find the J1939 checksum/CRC and counter signals.

    The signals are identified using their J1939-defined bit layouts,
    not GenSigFuncType or signal names.

    Args:
        message: cantools message object.
        crc_type: J1939 CRC/checksum type A, C, D or E.
        counter_type: J1939 counter type a, d or f.

    Returns:
        Tuple:
            (crc_signal, counter_signal)
    """
    crc_layout = J1939_CRC_SIGNAL_LAYOUTS[crc_type]
    counter_layout = J1939_COUNTER_SIGNAL_LAYOUTS[counter_type]

    crc_signal = _find_dbc_signal_by_layout(
        message=message,
        role=f"J1939 CRC/checksum type {crc_type}",
        start_bit=crc_layout["start_bit"],
        length=crc_layout["length"],
        byte_order=crc_layout["byte_order"],
    )

    counter_signal = _find_dbc_signal_by_layout(
        message=message,
        role=f"J1939 counter type {counter_type}",
        start_bit=counter_layout["start_bit"],
        length=counter_layout["length"],
        byte_order=counter_layout["byte_order"],
    )

    return crc_signal, counter_signal


def build_library_ir(selected_items, library_name, dbs, tree, version, message_modes, embedded=False, with_units=False,
                     generate_counter=True, generate_crc=True, generate_callback=True):
    validate_identifier(library_name, "Library prefix")
    selected_messages = {}

    for item in selected_items:
        item_type = tree.item(item, "values")[0]
        if item_type == "Signal":
            parent = tree.parent(item)
            msg_name = _selection_key(tree, parent)
            sig_name = tree.item(item, "text")
            selected_messages.setdefault(msg_name, []).append(sig_name)

    messages = []

    message_modes_by_name = {}

    for item_id, flags in message_modes.items():
        msg_name = _selection_key(tree, item_id)
        message_modes_by_name[msg_name] = flags

    name_counts = Counter(message.name for db in dbs for message in db.messages)
    used_names = set()
    used_ids = set()
    for db_index, db in enumerate(dbs):
        for message in db.messages:
            identity = (db_index, message.frame_id, message.is_extended_frame)
            key = identity if identity in selected_messages else message.name
            if key not in selected_messages:
                continue
            if isinstance(key, str) and name_counts[message.name] > 1:
                raise ValueError(f"Message name '{message.name}' is ambiguous across databases; select it by database identity.")
            if message.name in used_names:
                raise ValueError(f"Selected messages share the generated name '{message.name}'. Rename one message or generate separate libraries.")
            if message.frame_id in used_ids:
                raise ValueError(f"Selected messages share CAN ID 0x{message.frame_id:X}; ID lookup requires unique IDs.")
            used_names.add(message.name)
            used_ids.add(message.frame_id)
            _validate_message(message, db)

            selected_signal_names = set(
                selected_messages[key]
            )

            j1939_crc_type, j1939_counter_type = (
                _parse_j1939_crc_counter_attribute(message)
            )

            dbc_j1939_crc_signal = None
            dbc_j1939_counter_signal = None

            if j1939_crc_type is not None and j1939_counter_type is not None:
                if message.length != 8:
                    raise ValueError(
                        f"Message '{message.name}' uses "
                        f"FsJ1939UseCrcAndCounter="
                        f"'{j1939_crc_type}{j1939_counter_type}', "
                        f"but its payload length is {message.length} bytes. "
                        f"Only 8-byte J1939 messages are supported."
                    )
                (
                    dbc_j1939_crc_signal,
                    dbc_j1939_counter_signal,
                ) = _find_j1939_protection_signals(
                    message=message,
                    crc_type=j1939_crc_type,
                    counter_type=j1939_counter_type,
                )

                # CRC and counter signals are required for generated J1939
                # output processing. Add them even when the user did not
                # select them explicitly in the GUI.

                selected_signal_names.add(dbc_j1939_crc_signal.name)
                selected_signal_names.add(dbc_j1939_counter_signal.name)

                for protection_signal in (dbc_j1939_crc_signal, dbc_j1939_counter_signal):
                    if protection_signal.is_signed or protection_signal.scale != 1 or protection_signal.offset != 0:
                        raise ValueError(f"J1939 protection signal '{protection_signal.name}' must be unsigned with factor 1 and offset 0.")

            signals = []
            code_names = {"base"}
            for sig in message.signals:
                if sig.name not in selected_signal_names:
                    continue

                gen_sig_func_type = 0

                if sig.dbc and sig.dbc.attributes and "GenSigFuncType" in sig.dbc.attributes:
                    gen_sig_func_type = int(sig.dbc.attributes["GenSigFuncType"].value)

                code_name = _make_signal_code_name(sig.name, sig.unit or "", with_units)
                validate_identifier(code_name, "Generated signal name")
                if code_name in code_names:
                    raise ValueError(f"Message '{message.name}' contains colliding generated signal name '{code_name}'.")
                code_names.add(code_name)
                if gen_sig_func_type == 2 and j1939_crc_type is None and (sig.start != 0 or sig.length != 8 or sig.is_signed):
                    raise ValueError(f"Ordinary CRC signal '{sig.name}' must be an unsigned 8-bit signal at bit 0.")
                initial = int(sig.raw_initial or 0)
                mask = (1 << sig.length) - 1
                if initial < (-(1 << (sig.length - 1)) if sig.is_signed else 0) or initial > mask:
                    raise ValueError(f"Initial value for '{sig.name}' does not fit its bit width.")
                raw_initial = initial & mask
                signed_initial = raw_initial - (1 << sig.length) if sig.is_signed and raw_initial & (1 << (sig.length - 1)) else raw_initial
                signals.append(
                    SignalIR(
                        name=sig.name,
                        code_name=code_name,
                        start_bit=sig.start,
                        length=sig.length,
                        is_big_endian=(sig.byte_order == "big_endian"),
                        is_signed=sig.is_signed,
                        factor=sig.scale,
                        offset=sig.offset,
                        minimum=sig.minimum or 0,
                        maximum=sig.maximum or 0,
                        unit=sig.unit or "",
                        receivers=list(sig.receivers or []),
                        raw_initial=raw_initial,
                        phys_initial=signed_initial * sig.scale + sig.offset,
                        gen_sig_func_type=gen_sig_func_type,
                        attributes={
                            k: v.value for k, v in sig.dbc.attributes.items()
                        } if sig.dbc and sig.dbc.attributes else {}
                    )
                )

            modes = message_modes_by_name.get(key, {"rx": False, "tx": False})

            cycle_time_fast = int(
                _get_message_attribute(
                    message,
                    "GenMsgCycleTimeFast",
                    0
                )
            )

            start_delay_time = int(
                _get_message_attribute(
                    message,
                    "GenMsgStartDelayTime",
                    0
                )
            )

            resolved_is_fd = _is_can_fd_message(message, db)

            j1939_crc_signal_code_name = None
            j1939_counter_signal_code_name = None
            j1939_counter_maximum = None
            j1939_counter_not_available = None

            if dbc_j1939_crc_signal is not None:
                crc_signal_ir = next(
                    (
                        signal
                        for signal in signals
                        if signal.name == dbc_j1939_crc_signal.name
                    ),
                    None
                )

                counter_signal_ir = next(
                    (
                        signal
                        for signal in signals
                        if signal.name == dbc_j1939_counter_signal.name
                    ),
                    None
                )

                if crc_signal_ir is None:
                    raise ValueError(
                        f"Internal generator error: J1939 CRC/checksum "
                        f"signal '{dbc_j1939_crc_signal.name}' was not "
                        f"added to message '{message.name}'.'"
                    )

                if counter_signal_ir is None:
                    raise ValueError(
                        f"Internal generator error: J1939 counter "
                        f"signal '{dbc_j1939_counter_signal.name}' was not "
                        f"added to message '{message.name}'."
                    )

                counter_layout = (
                    J1939_COUNTER_SIGNAL_LAYOUTS[
                        j1939_counter_type
                    ]
                )

                j1939_crc_signal_code_name = (
                    crc_signal_ir.code_name
                )

                j1939_counter_signal_code_name = (
                    counter_signal_ir.code_name
                )

                j1939_counter_maximum = (
                    counter_layout["maximum"]
                )

                j1939_counter_not_available = (
                    counter_layout["not_available"]
                )

            messages.append(
                MessageIR(
                    name=message.name,
                    frame_id=message.frame_id,
                    length=message.length,
                    dlc=get_dlc_from_data_length(message.length),
                    is_fd=resolved_is_fd,
                    is_j1939=_is_j1939_message(message, db),
                    is_extended=message.is_extended_frame,
                    cycle_time=message.cycle_time or 0,
                    senders=list(message.senders or []),
                    receivers=list(message.receivers or []),
                    signals=signals,
                    mode_rx=modes["rx"],
                    mode_tx=modes["tx"],
                    start_delay_time=start_delay_time,
                    cycle_time_fast=cycle_time_fast,
                    j1939_crc_type=j1939_crc_type,
                    j1939_counter_type=j1939_counter_type,
                    j1939_crc_signal_code_name=j1939_crc_signal_code_name,
                    j1939_counter_signal_code_name=j1939_counter_signal_code_name,
                    j1939_counter_maximum=j1939_counter_maximum,
                    j1939_counter_not_available=j1939_counter_not_available,
                )
            )

    if not messages:
        raise ValueError("No messages with selected signals were found.")
    _validate_generated_symbols(messages, library_name)
    return LibraryIR(
        library_name=library_name,
        generator_version=version,
        dbc_versions=[(db.name, db.version or "unknown") for db in dbs],
        messages=messages,
        current_date=datetime.now().strftime("%d.%m.%Y"),
        current_year=datetime.now().year,
        embedded=embedded,
        with_units=with_units,
        generate_counter=generate_counter,
        generate_crc=generate_crc,
        generate_callback=generate_callback
    )
