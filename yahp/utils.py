from typing import Any, Tuple


def ensure_tuple(x: Any) -> Tuple[Any, ...]:
    if isinstance(x, tuple):
        return x
    if isinstance(x, list):
        return tuple(x)
    if isinstance(x, dict):
        return tuple(x.values())
    return (x,)
