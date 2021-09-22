# pyright: strict

import argparse
import collections.abc
import os
from typing import Dict, List, Sequence, Tuple, Union, cast

import yaml

from yahp.types import JSON


def _get_inherits_paths(
    namespace: Dict[str, JSON],
    argument_path: List[str],
) -> List[Tuple[List[str], List[str]]]:
    paths: List[Tuple[List[str], List[str]]] = []
    for key, val in namespace.items():
        if key == "inherits":
            if isinstance(val, str):
                val = [val]
            val = cast(List[str], val)
            paths.append((argument_path, val))
        elif isinstance(val, collections.abc.Mapping):
            paths += _get_inherits_paths(
                namespace=val,
                argument_path=argument_path + [key],
            )
    return paths


def _data_by_path(
    namespace: JSON,
    argument_path: Sequence[Union[int, str]],
) -> JSON:
    for key in argument_path:
        # path_str = '.'.join(str(x) for x in argument_path)
        if isinstance(namespace, dict):
            assert isinstance(key, str)
            namespace = namespace[key]
        elif isinstance(namespace, list):
            assert isinstance(key, int)
            namespace = namespace[key]
        else:
            raise ValueError("Path must be empty unless if list or dict")
    return namespace


class _OverridenValue:

    def __init__(self, val: JSON):
        self.val = val


def _unwrap_overriden_value_dict(data: Dict[str, JSON]):
    for key, val in data.items():
        if isinstance(val, collections.abc.Mapping):
            _unwrap_overriden_value_dict(val)
        elif isinstance(val, _OverridenValue):
            data[key] = val.val


def _recursively_update_leaf_data_items(
    update_namespace: Dict[str, JSON],
    update_data: JSON,
    update_argument_path: List[str],
):
    """
    This function exists to ensure that overrides don't overwrite dictionaries with other keyed values
    i.e. a["b"] = {1:1, 2:2}
    a.update({"b":{1:3}}) -> a = {"b":{1:3}} and 2:2 is removed
    Ensures only leaves are updated so behavior becomes a = {"b":{1:3, 2:2}}
    usage:
        a = {"b":{1:1, 2:2}}
        _recursively_update_leaf_data_items(a, {1:3}, ["b"]) -> {"b":{1:3, 2:2}}
    """
    if isinstance(update_data, collections.abc.Mapping):
        for key, val in update_data.items():
            _recursively_update_leaf_data_items(
                update_namespace=update_namespace,
                update_data=val,
                update_argument_path=update_argument_path + [key],
            )
    else:
        # Must be a leaf
        inner_namespace = update_namespace
        new_inner: Dict[str, JSON] = {}
        if len(update_argument_path) <= 1:
            new_inner = inner_namespace

        for key in update_argument_path[:-1]:
            key_element: JSON = inner_namespace.get(key, None)
            if key_element is None or not isinstance(key_element, dict):
                # If the nested item isn't a dict, it will need to be to store leaves
                key_element = {}
                inner_namespace[key] = key_element
            assert isinstance(key_element, dict)
            inner_namespace = key_element
            new_inner = key_element

        new_inner_value = new_inner.get(update_argument_path[-1], None)
        if new_inner_value is None or isinstance(
                new_inner_value,
                _OverridenValue,
        ) or (isinstance(new_inner_value, dict) and "inherits" in new_inner_value.keys()):
            new_inner[update_argument_path[-1]] = _OverridenValue(update_data)  # type: ignore


def load_yaml_with_inheritance(yaml_path: str) -> Dict[str, JSON]:
    abs_path = os.path.abspath(yaml_path)
    file_directory = os.path.dirname(abs_path)
    try:
        with open(abs_path, 'r') as f:
            data: JSON = yaml.full_load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Inherits path not found for {abs_path}") from e

    assert isinstance(data, dict)

    inherit_paths = sorted(_get_inherits_paths(data, []), key=lambda x: len(x[0]))
    for arg_path_parts, yaml_file_s in inherit_paths:
        for new_yaml_path in yaml_file_s:
            sub_yaml_path = os.path.abspath(os.path.join(file_directory, new_yaml_path))
            sub_yaml_data = load_yaml_with_inheritance(yaml_path=sub_yaml_path)
            try:
                sub_data = _data_by_path(namespace=sub_yaml_data, argument_path=arg_path_parts)
            except KeyError as e:
                raise KeyError(f"Failed to load item from inherited sub_yaml: {sub_yaml_path}") from e
            _recursively_update_leaf_data_items(
                update_namespace=data,
                update_data=sub_data,
                update_argument_path=arg_path_parts,
            )
        inherits_key_dict = _data_by_path(namespace=data, argument_path=arg_path_parts)
        if isinstance(inherits_key_dict, dict) and "inherits" in inherits_key_dict:
            del inherits_key_dict["inherits"]
    _unwrap_overriden_value_dict(data)
    return data


def preprocess_yaml_with_inheritance(yaml_path: str, output_yaml_path: str) -> None:
    data = load_yaml_with_inheritance(yaml_path)
    with open(output_yaml_path, "w+") as f:
        yaml.dump(data, f, explicit_end=False, explicit_start=False, indent=2, default_flow_style=False)  # type: ignore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str, help="Input file")
    parser.add_argument("output_file", type=str, help="Output file")
    args = parser.parse_args()
    preprocess_yaml_with_inheritance(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
