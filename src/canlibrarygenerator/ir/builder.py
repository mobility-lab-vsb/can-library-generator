from .models import LibraryIR, MessageIR, SignalIR
from ..utils.can_utils import get_dlc_from_data_length
from datetime import datetime

import re


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


def _get_message_enum_attribute_name(message, attribute_name: str) -> str | None:
    if (
        not message.dbc
        or not message.dbc.attributes
        or attribute_name not in message.dbc.attributes
    ):
        return None

    attribute = message.dbc.attributes[attribute_name]
    value = attribute.value

    if isinstance(value, str):
        return value

    definition = getattr(attribute, "definition", None)
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


def _is_can_fd_message(message) -> bool:
    """
    Determine whether a message uses CAN FD.

    For J1939PG messages, the J1939PgAppearanceOnBus attribute is used:
        CAN_EXTENDED   -> Classic CAN
        CANFD_EXTENDED -> CAN FD
        Default        -> fallback to cantools message.is_fd

    For all non-J1939 messages, cantools message.is_fd is used directly.
    """
    frame_format = _normalize_enum_name(
        _get_message_enum_attribute_name(
            message,
            "VFrameFormat"
        )
    )

    # Non-J1939 messages are handled directly by cantools.
    if frame_format != "J1939PG":
        return bool(message.is_fd)

    appearance = _normalize_enum_name(
        _get_message_enum_attribute_name(
            message,
            "J1939PgAppearanceOnBus"
        )
    )

    if appearance == "CANFD_EXTENDED":
        return True

    if appearance == "CAN_EXTENDED":
        return False

    # Default, missing or unknown value falls back to cantools.
    return bool(message.is_fd)

def build_library_ir(selected_items, library_name, dbs, tree, version, message_modes, embedded=False, with_units=False,
                     generate_counter=True, generate_crc=True, generate_callback=True):
    selected_messages = {}

    for item in selected_items:
        item_type = tree.item(item, "values")[0]
        if item_type == "Signal":
            parent = tree.parent(item)
            msg_name = tree.item(parent, "text")
            sig_name = tree.item(item, "text")
            selected_messages.setdefault(msg_name, []).append(sig_name)

    messages = []

    message_modes_by_name = {}

    for item_id, flags in message_modes.items():
        msg_name = tree.item(item_id, "text")
        message_modes_by_name[msg_name] = flags

    for db in dbs:
        for message in db.messages:
            if message.name not in selected_messages:
                continue

            signals = []
            for sig in message.signals:
                if selected_messages[message.name] and sig.name not in selected_messages[message.name]:
                    continue

                gen_sig_func_type = 0

                if sig.dbc and sig.dbc.attributes and "GenSigFuncType" in sig.dbc.attributes:
                    gen_sig_func_type = int(sig.dbc.attributes["GenSigFuncType"].value)

                signals.append(
                    SignalIR(
                        name=sig.name,
                        code_name=_make_signal_code_name(sig.name, sig.unit or "", with_units),
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
                        raw_initial=sig.raw_initial or 0,
                        phys_initial=(sig.raw_initial or 0) * sig.scale + sig.offset,
                        gen_sig_func_type=gen_sig_func_type,
                        attributes={
                            k: v.value for k, v in sig.dbc.attributes.items()
                        } if sig.dbc and sig.dbc.attributes else {}
                    )
                )

            modes = message_modes_by_name.get(message.name, {"rx": False, "tx": False})

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

            resolved_is_fd = _is_can_fd_message(message)

            messages.append(
                MessageIR(
                    name=message.name,
                    frame_id=message.frame_id,
                    length=message.length,
                    dlc=get_dlc_from_data_length(message.length),
                    is_fd=resolved_is_fd,
                    is_extended=message.is_extended_frame,
                    cycle_time=message.cycle_time or 0,
                    senders=list(message.senders or []),
                    receivers=list(message.receivers or []),
                    signals=signals,
                    mode_rx=modes["rx"],
                    mode_tx=modes["tx"],
                    start_delay_time=start_delay_time,
                    cycle_time_fast=cycle_time_fast
                )
            )

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