from typing import Dict


def none_or(val, or_val):
    return val if val is not None else or_val


def drop_none(d: Dict):
    return {k: v for k, v in d.items() if v is not None}
