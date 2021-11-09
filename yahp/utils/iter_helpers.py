# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

from typing import Any, Dict, List, Tuple, TypeVar, Union

T = TypeVar("T")


def ensure_tuple(x: Union[T, Tuple[T, ...], List[T], Dict[Any, T]]) -> Tuple[T, ...]:
    """Converts ``x`` to a :class:`tuple`

    Args:
        x (Any):
            If ``x`` is a tuple, it is returned as-is.
            If ``x`` is a list, it is converted to a tuple and returned.
            If ``x`` is a dict, its values are converted to a tuple and returned.
            Otherwise, ``x``: is wrapped as a one-element tuple and returned.

    Returns:
        Tuple[Any, ...]: ``x``, as a tuple.
    """
    if isinstance(x, tuple):
        return x
    if isinstance(x, list):
        return tuple(x)
    if isinstance(x, dict):
        return tuple(x.values())
    return (x,)


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
