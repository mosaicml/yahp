# Copyright 2021 MosaicML. All Rights Reserved.

import os
import pathlib

import pytest
import yaml

from yahp.inheritance import (_recursively_update_leaf_data_items, _unwrap_overriden_value_dict,
                              preprocess_yaml_with_inheritance)


# Breaks because I removed nested inherits
# @pytest.mark.xfail
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

    assert actual_output == expected_output, f"{actual_output} != {expected_output}"


def check_update_equal(orig, target, update):
    _recursively_update_leaf_data_items(orig, update, [])
    _unwrap_overriden_value_dict(orig)
    assert orig == target, f"{orig} != {target}"


def check_update_not_equal(orig, target, update):
    _recursively_update_leaf_data_items(orig, update, [])
    _unwrap_overriden_value_dict(orig)
    assert orig != target, f"{orig} == {target}"


def test_empty_namespace():
    orig = {}
    target = {"a": 1, "b": {"c": 2}}
    check_update_equal(orig, target, target)


def test_empty_dict():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": {"c": 2}}
    check_update_equal(orig, target, {})


def test_empty_nested_key():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": {"c": 2}, "foo": {}}
    check_update_equal(orig, target, {"foo": {}})


def test_empty_nested_key_no_overwrite():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": {"c": 2}}
    update = {"b": {}}
    check_update_equal(orig, target, update)


# TODO: Add overwriting with None
@pytest.mark.xfail
def test_overwrite_simple_with_nonetype():
    orig = {"a": 1, "b": 'foo'}
    target = {"b": 'foo'}
    update = {"a": None}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_overwrite_absent_key():
    orig = {"a": 1, "b": 'foo'}
    target = {"a": 1, "b": 'foo'}
    update = {"c": None}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_overwrite_dict_with_nonetype():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1}
    update = {"b": None}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_overwrite_list_with_nonetype():
    orig = {"a": {"b": [{"c": [{"d": 'foo'}]}]}}
    target = {"a": {}}
    update = {"a": {"b": None}}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_overwrite_nested_dict_with_nonetype():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": {}}
    update = {"b": {"c": None}}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_overwrite_nested_list_with_nonetype():
    orig = {"a": {"b": [{"c": [{"d": 'foo'}]}]}}
    target = {"a": {"b": [{}]}}
    update = {"a": {"b": {"c": None}}}
    check_update_equal(orig, target, update)


# @pytest.mark.xfail
def test_update_list_of_dicts():
    orig = {"a": [{"b": 'foo'}, {"c": 'bar'}]}
    target = {"a": [{"b": 'baz'}, {"c": 'bar'}]}
    update = {"a": {"b": 'baz'}}
    check_update_equal(orig, target, update)


def test_update_list_of_dicts_nested2():
    orig = {"a": [{"b": {"c": 'foo'}}]}
    target = {"a": [{"b": {"c": 'foo'}}, {"d": 'bar'}]}
    update = {"a": {"d": "bar"}}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_update_list_of_dicts_nested():
    orig = {"a": [{"b": {"c": 'foo'}}, {"d": 'bar'}]}
    target = {"a": [{"b": {"c": 'baz'}}, {"d": 'bar'}]}
    update = {"a": {"b": {"c": 'baz'}}}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_update_nested_list_of_dicts():
    orig = {"a": {"b": [{"c": [{"d": 'foo'}]}]}}
    target = {"a": {"b": [{"c": [{"d": 'bar'}]}]}}
    update = {"a": {"b": {"c": {"d": 'bar'}}}}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_change_data_type_simple():
    orig = {"a": {"b": 'foo', "c": "bar"}}
    target = {"a": {"b": 42, "c": "bar"}}
    update = {"a": {"b": 42}}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_change_data_type_dict():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": "foo"}
    update = {"b": "foo"}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_change_data_type_list():
    orig = {"a": {"b": [{"c": [{"d": 'foo'}]}]}}
    target = {"a": {"b": 'foo'}}
    update = {"a": {"b": 'foo'}}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_change_data_type_list_nested():
    orig = {"a": {"b": [{"c": [{"d": 'foo'}]}]}}
    target = {"a": {"b": [{"c": 'foo'}]}}
    update = {"a": {"b": {"c": 'foo'}}}
    check_update_equal(orig, target, update)


def test_nested_not_equal():
    orig = {"a": 1, "b": {"c": 2}}
    target = {"a": 1, "b": {"c": 3}}
    update = {"b": {"c": 'foo'}}
    check_update_not_equal(orig, target, update)


def test_not_update_list():
    orig = {"a": [0, 1, 2], "b": "foo"}
    target = {"a": [3, 1, 2], "b": "foo"}
    update = {"a": [3]}
    check_update_not_equal(orig, target, update)


@pytest.mark.xfail
def test_docstring_example():
    orig = {"b": {1: 1, 2: 2}}
    target = {"b": {1: 3, 2: 2}}
    update = {"b": {1: 3}}
    check_update_equal(orig, target, update)


@pytest.mark.xfail
def test_actual_docstring_example():
    a = {"b": {1: 1, 2: 2}}
    _recursively_update_leaf_data_items(a, {1: 3}, ["b"])
    assert a == {"b": {1: 3, 2: 2}}


if __name__ == "__main__":
    # test_yaml_inheritance("/tmp")
    test_update_list_of_dicts_nested2()
    # test_update_list_of_dicts_nested()
    # test_not_update_list()
