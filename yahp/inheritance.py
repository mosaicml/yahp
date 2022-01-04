# Copyright 2021 MosaicML. All Rights Reserved.

from __future__ import annotations

import argparse
import collections.abc
import logging
import os
from typing import TYPE_CHECKING, Dict, List, Sequence, Tuple, Union, cast

import yaml

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
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
        elif isinstance(val, list):
            for ii, item in enumerate(val):
                if isinstance(item, collections.abc.Mapping):
                    _unwrap_overriden_value_dict(item)
                elif isinstance(item, _OverridenValue):
                    val[ii] = item.val
        elif isinstance(val, _OverridenValue):
            data[key] = val.val


def list_setdefault(data: List, key: str, default: Dict) -> Dict:
    for item in data:
        assert isinstance(item, dict), "List must be a list of single-item dictionaries"
        assert len(item) == 1, "List must be a list of single-item dictionaries"
        k, v = next(iter(item.items()))
        if k == key:
            return v  # Found it, return the value

    # Key wasn't found, set to default and append
    data.append({key: default})
    return default


def _recursively_update_leaf_data_items(
    update_namespace: Dict[str, JSON],
    update_data: JSON,
):
    """ Recursive function to update leaf data items in ``update_namespace`` with the data in ``update_data``.
    This function exists to ensure that overrides don't overwrite dictionaries with other keyed values
    i.e. a["b"] = {1:1, 2:2}
    a.update({"b":{1:3}}) -> a = {"b":{1:3}} and 2:2 is removed
    Ensures only leaves are updated so behavior becomes a = {"b":{1:3, 2:2}}
    usage:
        a = {"b":{1:1, 2:2}}
        _recursively_update_leaf_data_items(a, {1:3}, ["b"]) -> {"b":{1:3, 2:2}}
    """
    if update_data is None:
        return
    for key, val in update_data.items():
        if isinstance(val, collections.abc.Mapping):
            # Must refer to a sub-Hparams
            if isinstance(update_namespace, collections.abc.Mapping):
                # A dictionary of sub-Hparams
                _recursively_update_leaf_data_items(
                    update_namespace=update_namespace.setdefault(key, {}),
                    update_data=val,
                )
            elif isinstance(update_namespace, list):
                # A list of sub-Hparams
                _recursively_update_leaf_data_items(update_namespace=list_setdefault(update_namespace, key, {}),
                                                    update_data=val)
            else:
                raise TypeError("Expected dictionary or list of dictionaries")
        else:
            # Must be a leaf
            if isinstance(update_namespace, dict):
                update_namespace[key] = _OverridenValue(val)  # type: ignore
            else:
                raise TypeError("Expected last branch to be a dictionary")


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

    inherit_paths = sorted(_get_inherits_paths(data, []), key=lambda x: len(x[0]))
    for arg_path_parts, yaml_file_s in inherit_paths:
        for new_yaml_path in yaml_file_s:
            if not os.path.isabs(new_yaml_path):
                sub_yaml_path = os.path.abspath(os.path.join(file_directory, new_yaml_path))
            else:
                sub_yaml_path = new_yaml_path
            sub_yaml_data = load_yaml_with_inheritance(yaml_path=sub_yaml_path)
            try:
                sub_data = _data_by_path(namespace=sub_yaml_data, argument_path=arg_path_parts)
            except KeyError as e:
                logger.warn(f"Failed to load item from inherited sub_yaml: {sub_yaml_path}")
                continue
            _recursively_update_leaf_data_items(update_namespace=data, update_data=sub_data)
        inherits_key_dict = _data_by_path(namespace=data, argument_path=arg_path_parts)
        if isinstance(inherits_key_dict, dict) and "inherits" in inherits_key_dict:
            del inherits_key_dict["inherits"]
    _unwrap_overriden_value_dict(data)
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
