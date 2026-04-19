from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class SignalIR:
    name: str
    start_bit: int
    length: int
    byte_order: str
    is_signed: bool
    factor: float
    offset: float
    minimum: float
    maximum: float
    unit: str
    receivers: List[str]
    raw_initial: int
    phys_initial: float
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


@dataclass
class LibraryIR:
    library_name: str
    generator_version: str
    dbc_versions: List[tuple]
    messages: List[MessageIR]
    current_date: str
    current_year: int