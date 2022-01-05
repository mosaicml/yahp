# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

import argparse
import collections.abc
import logging
import os
from typing import TYPE_CHECKING, Dict, List, Sequence, Tuple, Union, cast

import yaml

from yahp.utils.iter_helpers import ListOfSingleItemDict, is_list_of_single_item_dicts

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from yahp.types import JSON


def _get_inherits_paths(
    namespace: Dict[str, JSON],
    argument_path: List[str],
) -> List[Tuple[List[str], List[str]]]:
    """Finds all instances of 'inherits' in the dict `namespace`, along with their nested paths

    Args:
        namespace (Dict[str, JSON]): Nested dictionary in which to search
        argument_path (List[str]): List of keys in the nested dict relative to the original namespace

    Returns:
        List[Tuple[List[str], List[str]]]: List of paths and the files to be inherited from at each of those paths
    """
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
        if isinstance(namespace, dict):
            assert isinstance(key, str)
            namespace = namespace[key]
        elif is_list_of_single_item_dicts(namespace):  #type: ignore
            assert isinstance(key, str)
            namespace = ListOfSingleItemDict(namespace)[key]
        elif isinstance(namespace, list):
            assert isinstance(key, int)
            namespace = namespace[key]
        else:
            raise ValueError("Path must be empty unless if list or dict")
    return namespace


def _ensure_path_exists(namespace: JSON, argument_path: Sequence[Union[int, str]]) -> None:
    for key in argument_path:
        if isinstance(namespace, dict):
            assert isinstance(key, str)
            namespace = namespace.setdefault(key, {})
        elif is_list_of_single_item_dicts(namespace):  #type: ignore
            assert isinstance(key, str)
            namespace = ListOfSingleItemDict(namespace)
            if key not in namespace:
                namespace[key] = {}
            namespace = namespace[key]
        elif isinstance(namespace, list):
            assert isinstance(key, int)
            namespace = namespace[key]  # TODO: try except to verify key in range
        else:
            raise ValueError("Path must be empty unless if list or dict")


class _OverridenValue:

    def __init__(self, val: JSON):
        self.val = val


def _unwrap_overridden_value_dict(data: Dict[str, JSON]):
    for key, val in data.items():
        if isinstance(val, collections.abc.Mapping):
            _unwrap_overridden_value_dict(val)
        elif is_list_of_single_item_dicts(val):
            for item in val:
                _unwrap_overridden_value_dict(item)
        elif isinstance(val, _OverridenValue):
            data[key] = val.val


def _recursively_update_leaf_data_items(
    update_namespace: Dict[str, JSON],
    update_data: JSON,
    update_argument_path: List[str],
):
    if isinstance(update_data, collections.abc.Mapping):
        _ensure_path_exists(update_namespace, update_argument_path)
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

        # Traverse the tree to the final branch
        for key in update_argument_path[:-1]:
            key_element = None
            if isinstance(inner_namespace, collections.abc.Mapping):
                # Simple dict
                key_element: JSON = inner_namespace.get(key)
            elif is_list_of_single_item_dicts(inner_namespace):
                # List of one-item dicts
                inner_namespace = ListOfSingleItemDict(inner_namespace)
                if key in inner_namespace:
                    key_element: JSON = inner_namespace[key]
            # key_element is None otherwise

            # This needs to be a branch, so make it an empty dict
            if key_element is None or not (isinstance(key_element, dict) or is_list_of_single_item_dicts(key_element)):
                key_element = {}
                inner_namespace[key] = key_element

            assert isinstance(key_element, dict) or is_list_of_single_item_dicts(key_element)

            # These two values are shared. Why not just use inner_namespace???
            inner_namespace = key_element
            new_inner = key_element

        if isinstance(new_inner, collections.abc.Mapping):
            new_inner_value = new_inner.get(update_argument_path[-1])
        else:
            # List of single-item dicts
            new_inner = ListOfSingleItemDict(new_inner)
            if update_argument_path[-1] in new_inner:
                new_inner_value = new_inner[update_argument_path[-1]]
            else:
                new_inner_value = None

        if new_inner_value is None or isinstance(
                new_inner_value,
                _OverridenValue,
        ) or (isinstance(new_inner_value, dict) and "inherits" in new_inner_value.keys()):
            new_inner[update_argument_path[-1]] = _OverridenValue(update_data)  # type: ignore


def load_yaml_with_inheritance(yaml_path: str) -> Dict[str, JSON]:
    """Loads a YAML file with inheritance.

    Inheritance allows one YAML file to include data from another yaml file.

    Example:

    Given two yaml files -- ``foo.yaml`` and ``bar.yaml``:

    ``foo.yaml``:

    .. code-block:: yaml

        foo:
            inherits:
                - bar.yaml

    ``bar.yaml``:

    .. code-block:: yaml

        foo:
            param: val
            other:
                whatever: 12
        tomatoes: 11


    Then this function will return one dictionary with:

    .. code-block:: python

        {
            "foo": {
                "param": "val",
                "other: {
                    "whatever": 12
                }
            },
        }

    Args:
        yaml_path (str): The filepath to the yaml to load.

    Returns:
        JSON Dictionary: The flattened YAML, with inheritance stripped.
    """
    abs_path = os.path.abspath(yaml_path)
    file_directory = os.path.dirname(abs_path)
    with open(abs_path, 'r') as f:
        data: JSON = yaml.full_load(f)

    if data is None:
        data = {}

    assert isinstance(data, dict)

    # Get all instances of 'inherits' in the YAML, sorted by depth in the nested dict
    inherit_paths = sorted(_get_inherits_paths(data, []), key=lambda x: len(x[0]))

    for nested_keys, inherit_yamls in inherit_paths:
        for inherit_yaml in inherit_yamls:
            if not os.path.isabs(inherit_yaml):
                # Allow paths relative to the provided YAML
                inherit_yaml = os.path.abspath(os.path.join(file_directory, inherit_yaml))

            # Recursively load the YAML to inherit from
            inherit_data_full = load_yaml_with_inheritance(yaml_path=inherit_yaml)
            try:
                # Select out just the portion specified by nested_keys
                inherit_data = _data_by_path(namespace=inherit_data_full, argument_path=nested_keys)
            except KeyError as e:
                logger.warn(f"Failed to load item from inherited YAML file: {inherit_yaml}")
                continue

            # Insert any new keys from inherit_data into data
            _recursively_update_leaf_data_items(
                update_namespace=data,
                update_data=inherit_data,
                update_argument_path=nested_keys,
            )

        # Carefully remove the 'inherits' key from the nested data dict
        inherits_key_dict = _data_by_path(namespace=data, argument_path=nested_keys)
        if isinstance(inherits_key_dict, dict) and "inherits" in inherits_key_dict:
            del inherits_key_dict["inherits"]

    # Resolve all newly added values in data
    _unwrap_overridden_value_dict(data)
    return data


def preprocess_yaml_with_inheritance(yaml_path: str, output_yaml_path: str) -> None:
    """Helper function to preprocess yaml with inheritance and dump it to another file

    See :meth:`load_yaml_with_inheritance` for how inheritance works.

    Args:
        yaml_path (str): Filepath to load
        output_yaml_path (str): Filepath to write flattened yaml to.
    """
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
