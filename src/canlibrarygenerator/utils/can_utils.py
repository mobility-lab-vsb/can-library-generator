data_length_to_dlc = {
    0: 0,
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    12: 9,
    16: 10,
    20: 11,
    24: 12,
    32: 13,
    48: 14,
    64: 15
}


def get_dlc_from_data_length(data_length: int) -> int | None:
    """Convert CAN/CAN-FD payload length to DLC."""
    return data_length_to_dlc.get(data_length)