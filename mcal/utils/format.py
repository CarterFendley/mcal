def bytes_to_human_readable(bytes: float, decimal: bool = True) -> str:
    units = ("", "K", "M", "G", "T", "P", "E", "Z")
    if not decimal:
        units = [""] + [f"{u}i" for u in units if u != ""]
        base = 1024.0
    else:
        base = 1000.0

    for u in units:
        if abs(bytes) < base:
            return f"{bytes:3.1f}{u}B"
        bytes /= base

    # Catch all
    if not decimal:
        return f"{bytes:.1f}YiB"
    return f"{bytes:.1f}YB"