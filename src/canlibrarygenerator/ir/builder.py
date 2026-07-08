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

def build_library_ir(selected_items, library_name, dbs, tree, version, message_modes, embedded=False, with_units=False):
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

                print(
                    sig.name,
                    gen_sig_func_type
                )

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

            cycle_time_fast = 0
            try:
                if (
                        message.dbc and
                        message.dbc.attributes and
                        "GenMsgCycleTimeFast" in message.dbc.attributes
                ):
                    cycle_time_fast = message.dbc.attributes["GenMsgCycleTimeFast"].value
            except Exception:
                cycle_time_fast = 0

            messages.append(
                MessageIR(
                    name=message.name,
                    frame_id=message.frame_id,
                    length=message.length,
                    dlc=get_dlc_from_data_length(message.length),
                    is_fd=message.is_fd,
                    is_extended=message.is_extended_frame,
                    cycle_time=message.cycle_time or 0,
                    senders=list(message.senders or []),
                    receivers=list(message.receivers or []),
                    signals=signals,
                    mode_rx=modes["rx"],
                    mode_tx=modes["tx"],
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
        with_units=with_units
    )