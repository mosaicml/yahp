import re
from typing import Any, Dict, Tuple, TypeVar


def ensure_tuple(x: Any) -> Tuple[Any, ...]:
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
    if len(val) != 1:
        raise ValueError(f"dict has {len(val)} keys, expecting 1")
    return list(val.items())[0]
