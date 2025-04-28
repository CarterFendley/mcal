from typing import Tuple


def bytes_units(bytes: float, decimal: bool = True) -> Tuple[float, float, str]:
    """
    Convert bytes to the most readable units

    Args:
        bytes (float): The input bytes.
        decimal (bool, optional): If decimal units should be used. Defaults to True.

    Returns:
        Tuple[float, float, str]: value, base, unit
    """
    units = ("", "K", "M", "G", "T", "P", "E", "Z")
    if not decimal:
        units = [""] + [f"{u}i" for u in units if u != ""]
        base = 1024.0
    else:
        base = 1000.0

    num_divisions = 0
    for u in units:
        if abs(bytes) < base:
            return bytes, base**num_divisions, f"{u}B"

        bytes /= base
        num_divisions += 1

    # Catch all
    if not decimal:
        return bytes, base**num_divisions, "YiB"
    return bytes, base**num_divisions, "YB"


def bytes_to_human_readable(bytes: float, decimal: bool = True) -> str:
    value, _, units = bytes_units(bytes, decimal=decimal)

    return f"{value:3.1f}{units}"