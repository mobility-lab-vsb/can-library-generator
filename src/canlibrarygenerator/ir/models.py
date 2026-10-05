from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class SignalIR:
    name: str
    code_name: str
    start_bit: int
    length: int
    is_big_endian: bool
    is_signed: bool
    factor: float
    offset: float
    minimum: float
    maximum: float
    unit: str
    receivers: List[str]
    raw_initial: int
    phys_initial: float
    gen_sig_func_type: int = 0
    attributes: Dict[str, int] = field(default_factory=dict)


@dataclass
class MessageIR:
    name: str
    frame_id: int
    length: int
    dlc: int
    is_fd: bool
    is_extended: bool
    cycle_time: int
    senders: List[str]
    receivers: List[str]
    signals: List[SignalIR]
    mode_rx: bool
    mode_tx: bool
    start_delay_time: int
    cycle_time_fast: int = 0
    j1939_crc_type: Optional[str] = None
    j1939_counter_type: Optional[str] = None
    j1939_crc_signal_code_name: Optional[str] = None
    j1939_counter_signal_code_name: Optional[str] = None
    j1939_counter_maximum: Optional[int] = None
    j1939_counter_not_available: Optional[int] = None


@dataclass
class LibraryIR:
    library_name: str
    generator_version: str
    dbc_versions: List[tuple]
    messages: List[MessageIR]
    current_date: str
    current_year: int
    embedded: bool = False
    with_units: bool = False
    generate_counter: bool = True
    generate_crc: bool = True
    generate_callback: bool = True