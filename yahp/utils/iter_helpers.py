# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Tuple, TypeVar, Union

if TYPE_CHECKING:
    from yahp.types import JSON

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


def list_to_deduplicated_dict(list_of_dict: List[Union[str, JSON]],
                              allow_str: bool = False,
                              separator: str = '+') -> JSON:
    """Converts a list of single-item dictionaries to a dictionary, deduplicating keys along the way

    Args:
        list_of_dict (List[Dict[str, Any]]): A list of single-element dictionaries
        allow_str (bool, optional): If True, list can contain strings, which will be added as keys with None values.
                                    Defaults to False.
        separator (str, optional): The separator to use for deduplication. Default '+'.

    Returns:
        Dict[str, Dict]: Deduplicated dictionary
    """

    data: JSON = {}
    counter: Dict[str, int] = {}
    for item in list_of_dict:
        if isinstance(item, str) and allow_str:
            k, v = item, None
        elif isinstance(item, dict):
            # item should have only one key-value pair
            k, v = extract_only_item_from_dict(item)
        else:
            raise TypeError(f"Expected list of dictionaries, got {type(item)}")
        if k in data:
            # Deduplicate by add '+<counter>'
            counter[k] += 1
            k = "".join((k, separator, str(counter[k] - 1)))
        else:
            counter[k] = 1
        data[k] = v
    return data
