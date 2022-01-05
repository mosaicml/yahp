# Copyright 2021 MosaicML. All Rights Reserved.

import copy
import os
import pathlib

import pytest
import yaml

from yahp.inheritance import (_OverridenValue, _recursively_update_leaf_data_items, _unwrap_overridden_value_dict,
                              preprocess_yaml_with_inheritance)

"""
TODO:
Insertion tests
- Test insert simple type into nested dict
- Test insert list type into nested dict
- Test insert nested dict into nested dict
- Test insert single-item list into nested dict
- Test insert simple type into single-item list
- Test insert list type into single-item list
- Test insert nested dict into single-item list
- Test insert single-item list into single-item list

Does not overwrite
- Test that simple types do not overwrite
- Test that list types do not overwrite
- Test that nested dicts do not overwrite
- Test that single-item lists do not overwrite

Empty checks
- Test empty update into nested dict
- Test empty update into single-item list
- Test update into empty nested dict
- Test update into None

YAML checks
- Test absolute path inheritance
- Test relative path inheritance
- Test sub-level inheritance
- Test second order inheritance
- Test inheritance order matters
"""

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
    _unwrap_overridden_value_dict(orig)
    assert orig == target, f"{orig} != {target}"


def check_update_not_equal(orig, target, update):
    _recursively_update_leaf_data_items(orig, update, [])
    _unwrap_overridden_value_dict(orig)
    assert orig != target, f"{orig} == {target}"


@pytest.fixture
def nested_dict():
    return {"a": {"b": {"c": 1}}}

@pytest.fixture
def nested_dict_none():
    return {"a": {"b": {"c": None}}}

@pytest.fixture
def nested_dict_overridden():
    return {"a": {"b": {"c": _OverridenValue(1)}}}

@pytest.fixture
def nested_list():
    return {"a": [{"b": {"c": 1}}]}

@pytest.fixture
def simple_update():
    return {"a": {"d": 'foo'}}

@pytest.fixture
def list_update():
    return {"a": {"d": ['foo', 'bar']}}

@pytest.fixture
def nested_dict_update():
    return {"a": {"d": {"e": 'foo'}}}

@pytest.fixture
def nested_list_update():
    return {"a": {"d": [{"e": 'foo'}]}}


# Insertion tests
## Into nested dict
def test_insert_simple_nested_dict(nested_dict, simple_update):
    target = copy.deepcopy(nested_dict)
    target["a"]["d"] = simple_update["a"]["d"]
    check_update_equal(nested_dict, target, simple_update)

def test_insert_list_nested_dict(nested_dict, list_update):
    target = copy.deepcopy(nested_dict)
    target["a"]["d"] = list_update["a"]["d"]
    check_update_equal(nested_dict, target, list_update)

def test_insert_nested_dict_nested_dict(nested_dict, nested_dict_update):
    target = copy.deepcopy(nested_dict)
    target["a"]["d"] = nested_dict_update["a"]["d"]
    check_update_equal(nested_dict, target, nested_dict_update)

def test_insert_nested_list_nested_dict(nested_dict, nested_list_update):
    target = copy.deepcopy(nested_dict)
    target["a"]["d"] = nested_list_update["a"]["d"]
    check_update_equal(nested_dict, target, nested_list_update)

## Into nested single-item list
def test_insert_simple_nested_list(nested_list, simple_update):
    target = copy.deepcopy(nested_list)
    target["a"].append({"d": simple_update["a"]["d"]})
    check_update_equal(nested_list, target, simple_update)

def test_insert_list_nested_list(nested_list, list_update):
    target = copy.deepcopy(nested_list)
    target["a"].append({"d": list_update["a"]["d"]})
    check_update_equal(nested_list, target, list_update)

def test_insert_nested_dict_nested_list(nested_list, nested_dict_update):
    target = copy.deepcopy(nested_list)
    target["a"].append({"d": nested_dict_update["a"]["d"]})
    check_update_equal(nested_list, target, nested_dict_update)

def test_insert_nested_list_nested_list(nested_list, nested_list_update):
    target = copy.deepcopy(nested_list)
    target["a"].append({"d": nested_list_update["a"]["d"]})
    check_update_equal(nested_list, target, nested_list_update)

# Does not overwrite
def test_no_overwrite_on_conflict_simple(nested_dict, simple_update):
    target = copy.deepcopy(nested_dict)
    # Create conflict at a.b.c
    conflict = {"a": {"b": {"c": simple_update["a"]["d"]}}}
    check_update_equal(nested_dict, target, conflict)

def test_no_overwrite_on_conflict_list(nested_dict, list_update):
    target = copy.deepcopy(nested_dict)
    # Create conflict at a.b.c
    conflict = {"a": {"b": {"c": list_update["a"]["d"]}}}
    check_update_equal(nested_dict, target, conflict)

@pytest.mark.xfail # TODO: Look into why this fails. Is it expected?
def test_no_overwrite_on_conflict_nested_dict(nested_dict, nested_dict_update):
    target = copy.deepcopy(nested_dict)
    # Create conflict at a.b.c
    conflict = {"a": {"b": {"c": nested_dict_update["a"]["d"]}}}
    check_update_equal(nested_dict, target, conflict)

def test_no_overwrite_on_conflict_nested_list(nested_dict, nested_list_update):
    target = copy.deepcopy(nested_dict)
    # Create conflict at a.b.c
    conflict = {"a": {"b": {"c": nested_list_update["a"]["d"]}}}
    check_update_equal(nested_dict, target, conflict)

def test_no_overwrite_nested_list_on_conflict_simple(nested_list, simple_update):
    target = copy.deepcopy(nested_list)
    # Create conflict at a.b.c
    conflict = {"a": {"b": {"c": simple_update["a"]["d"]}}}
    check_update_equal(nested_list, target, conflict)

## Test overwrite works
def test_overwrite_none(nested_dict_none, simple_update):
    # Create conflict at a.b.c
    conflict = {"a": {"b": {"c": simple_update["a"]["d"]}}}
    target = copy.deepcopy(conflict)
    check_update_equal(nested_dict_none, target, conflict)

def test_overwrite_overridden(nested_dict_overridden, simple_update):
    # Create conflict at a.b.c
    conflict = {"a": {"b": {"c": simple_update["a"]["d"]}}}
    target = copy.deepcopy(conflict)
    check_update_equal(nested_dict_overridden, target, conflict)

## Test empty args
def test_empty_namespace(simple_update):
    target = copy.deepcopy(simple_update)
    check_update_equal({}, target, simple_update)

def test_empty_nested_namespace(simple_update):
    target = copy.deepcopy(simple_update)
    check_update_equal({"a": {}}, target, simple_update)


def test_empty_update(nested_dict):
    target = copy.deepcopy(nested_dict)
    check_update_equal(nested_dict, target, {})


def test_empty_nested_key(nested_dict):
    target = copy.deepcopy(nested_dict)
    check_update_equal(nested_dict, target, {"a": {}})


def test_empty_nested_key_nested_list(nested_list):
    target = copy.deepcopy(nested_list)
    check_update_equal(nested_list, target, {"a": {}})

# def


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


@pytest.mark.xfail
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
