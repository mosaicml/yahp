# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Tuple, TypeVar, Union, cast

if TYPE_CHECKING:
    from yahp.types import JSON

T = TypeVar('T')


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


K = TypeVar('K')
V = TypeVar('V')


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
        raise ValueError(f'dict has {len(val)} keys, expecting 1')
    return list(val.items())[0]


def list_to_deduplicated_dict(list_of_dict: List[JSON],
                              allow_str: bool = False,
                              separator: str = '+') -> Dict[str, JSON]:
    """Converts a list of single-item dictionaries to a dictionary, deduplicating keys along the way

    Args:
        list_of_dict (List[Dict[str, Any]]): A list of single-item dictionaries
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
            raise TypeError(f'Expected list of dictionaries, got {type(item)}')
        if k in data:
            # Deduplicate by add '+<counter>'
            counter[k] += 1
            k = ''.join((k, separator, str(counter[k] - 1)))
        else:
            counter[k] = 1
        data[k] = v
    return data


def is_list_of_single_item_dicts(obj: JSON) -> bool:
    """Whether the provided object is a list of single-item dictionaries

    Args:
        obj (List[Dict]) - Possible list of dictionaries

    Returns:
        True if ``obj`` is a list of single-item dictionaries
    """

    if isinstance(obj, ListOfSingleItemDict):
        return True

    if not isinstance(obj, list):
        return False

    for item in obj:
        if not (isinstance(item, dict) and len(item) == 1):
            return False

    return True


class ListOfSingleItemDict(list):
    """Simple list wrapper for a list of single-item dicts

    This enables string-based gets and sets. If there are duplicate keys in the list,
    the first one is retrieved/modified.
    """

    def __init__(self, data: List):
        if not is_list_of_single_item_dicts(data):
            raise TypeError('data must be list of single-item dictionaries')
        if isinstance(data, ListOfSingleItemDict):
            self._list = data._list
            self._data = data._data
        else:
            self._list = data
            self._data = cast(Dict, list_to_deduplicated_dict(data))

    def __contains__(self, key: Union[int, str]) -> bool:  # type: ignore
        return key in self._data

    def __getitem__(self, key: Union[int, str]) -> Any:
        if key in self._data:
            return self._data[key]
        if not isinstance(key, int):
            raise TypeError(f'Index should be of type {int}, not {type(key)}')
        return self._list.__getitem__(key)

    def __setitem__(self, key: Union[int, str], value: Any):
        for item in self._list:
            k, _ = extract_only_item_from_dict(item)
            if k == key:
                item[k] = value
                self._data[key] = value
                return
        self._list.append({key: value})
        self._data[key] = value
