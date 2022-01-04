# Copyright 2021 MosaicML. All Rights Reserved.

import os
import pathlib

import yaml

from yahp.inheritance import (_recursively_update_leaf_data_items, _unwrap_overriden_value_dict,
                              preprocess_yaml_with_inheritance)


def test_yaml_inheritance(tmpdir: pathlib.Path):
    inheritance_folder = os.path.join(os.path.dirname(__file__), "inheritance")
    input_file = os.path.join(inheritance_folder, "main.yaml")
    output_file = os.path.join(str(tmpdir), "output_yaml.yaml")

    preprocess_yaml_with_inheritance(input_file, output_file)
    expected_output_file = os.path.join(inheritance_folder, "composed.yaml")
    with open(expected_output_file, "r") as f:
        expected_output = yaml.full_load(f)

    with open(output_file, "r") as f:
        actual_output = yaml.full_load(f)

    assert actual_output == expected_output


def test_empty_dict():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": {"c": 2}}
    _recursively_update_leaf_data_items(orig, {})
    assert orig == target


def test_empty_nested_key():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": {"c": 2}, "foo": {}}
    _recursively_update_leaf_data_items(orig, {"foo": {}})
    assert orig == target


def test_empty_nested_key_no_overwrite():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": {"c": 2}}
    _recursively_update_leaf_data_items(orig, {"b": {}})
    assert orig == target


def test_update_list_of_dicts():
    orig = {"a": [{"b": 'foo'}, {"c": 'bar'}]}
    target = {"a": [{"b": 'baz'}, {"c": 'bar'}]}
    _recursively_update_leaf_data_items(orig, {"a": {"b": 'baz'}})
    assert orig == target


def test_update_list_of_dicts_nested():
    orig = {"a": [{"b": {"c": 'foo'}}, {"d": 'bar'}]}
    target = {"a": [{"b": {"c": 'baz'}}, {"d": 'bar'}]}
    _recursively_update_leaf_data_items(orig, {"a": {"b": {"c": 'baz'}}})
    _unwrap_overriden_value_dict(orig)
    assert orig == target, f"{orig} != {target}"


def test_not_update_list():
    orig = {"a": [0, 1, 2], "b": "foo"}
    target = {"a": [3, 1, 2], "b": "foo"}
    _recursively_update_leaf_data_items(orig, {"a": [3]})
    _unwrap_overriden_value_dict(orig)
    assert orig != target, f"{orig} == {target}"


if __name__ == "__main__":
    test_update_list_of_dicts()
    # test_update_list_of_dicts_nested()
    # test_not_update_list()
