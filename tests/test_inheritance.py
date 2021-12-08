# Copyright 2021 MosaicML. All Rights Reserved.

import os
import pathlib

import yaml

from yahp.inheritance import _recursively_update_leaf_data_items, preprocess_yaml_with_inheritance


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
    _recursively_update_leaf_data_items(orig, {}, [])
    assert orig == target


def test_empty_nested_key():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": {"c": 2}, "foo": {}}
    _recursively_update_leaf_data_items(orig, {"foo": {}}, [])
    assert orig == target


def test_empty_nested_key_no_overwrite():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": {"c": 2}}
    _recursively_update_leaf_data_items(orig, {"b": {}}, [])
    assert orig == target
