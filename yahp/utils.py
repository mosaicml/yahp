from __future__ import annotations

import re
from typing import Any, Dict, Tuple, TypeVar


def ensure_tuple(x: Any) -> Tuple[Any, ...]:
    """Converts :param x: to a :class:`tuple`

    Args:
        x (Any):
            If :param x: is a tuple, it is returned as-is.
            If :param x: is a list, it is converted to a tuple and returned.
            If :param x: is a dict, its values are converted to a tuple and returned.
            Otherwise, :param x: is wrapped as a one-element tuple and returned.

    Returns:
        Tuple[Any, ...]: :param x:, as a tuple.
    """
    if isinstance(x, tuple):
        return x
    if isinstance(x, list):
        return tuple(x)
    if isinstance(x, dict):
        return tuple(x.values())
    return (x,)


def camel_to_snake(name: str):
    # from https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


K = TypeVar("K")
V = TypeVar("V")


def extract_only_item_from_dict(val: Dict[K, V]) -> Tuple[K, V]:
    """Extracts the only item from a dict and returns it .

    Args:
        val (Dict[K, V]): A dictionary which should contain only one entry

    Raises:
        ValueError: Raised if the dictionary does not contain 1 item

    Returns:
        Tuple[K, V]: The key, value pair of the only item
    """
    if len(val) != 1:
        raise ValueError(f"dict has {len(val)} keys, expecting 1")
    return list(val.items())[0]
