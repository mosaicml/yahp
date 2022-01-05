# Copyright 2021 MosaicML. All Rights Reserved.

import copy
import os
import pathlib

import pytest
import yaml

from yahp.inheritance import (_OverriddenValue, _recursively_update_leaf_data_items, _unwrap_overridden_value_dict,
                              load_yaml_with_inheritance, preprocess_yaml_with_inheritance)


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
    return {"a": {"b": {"c": _OverriddenValue(1)}}}

@pytest.fixture
def nested_dict_inherits():
    return {"a": {"b": {"c": {"inherits": []}}}}

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

def test_overwrite_inherits(nested_dict_inherits, simple_update):
    # Create conflict at a.b.c
    conflict = {"a": {"b": {"c": simple_update["a"]["d"]}}}
    target = copy.deepcopy(conflict)
    check_update_equal(nested_dict_inherits, target, conflict)

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

## YAML tests
@pytest.mark.parametrize("absolute", (False, True))
def test_inheritance_absolute_path(nested_dict, simple_update, tmpdir, absolute):
    # Write update to inherits file
    inherits_file = os.path.join(tmpdir, "inherits.yaml")
    with open(inherits_file, "w") as fh:
        yaml.dump(simple_update, fh)

    if not absolute:  # Use relative path
        inherits_file = "inherits.yaml"
    base = copy.deepcopy(nested_dict)
    base["a"]["inherits"] = [inherits_file]

    # Write base yaml to file
    base_file = os.path.join(tmpdir, "base.yaml")
    with open(base_file, "w") as fh:
        yaml.dump(base, fh)

    # Get target
    target = copy.deepcopy(nested_dict)
    target["a"]["d"] = simple_update["a"]["d"]
    output = load_yaml_with_inheritance(base_file)
    assert output == target

def test_inheritance_sublevel(nested_dict, simple_update, tmpdir):
    # Write update to inherits file
    inherits_file = os.path.join(tmpdir, "inherits.yaml")
    with open(inherits_file, "w") as fh:
        yaml.dump(simple_update, fh)

    # Place 'inherits' under a.d
    base = copy.deepcopy(nested_dict)
    base["a"]["d"] = {"inherits": [inherits_file]}

    # Write base yaml to file
    base_file = os.path.join(tmpdir, "base.yaml")
    with open(base_file, "w") as fh:
        yaml.dump(base, fh)

    # Get target
    target = copy.deepcopy(nested_dict)
    target["a"]["d"] = simple_update["a"]["d"]
    output = load_yaml_with_inheritance(base_file)
    assert output == target

def test_inheritance_second_order(nested_dict, simple_update, tmpdir):
    inherits_file_1 = os.path.join(tmpdir, "inherits1.yaml")
    inherits_file_2 = os.path.join(tmpdir, "inherits2.yaml")

    # Write second order inherits file
    with open(inherits_file_2, "w") as fh:
        yaml.dump(simple_update, fh)

    # Write first order inherits
    first_order = {"a": {"inherits": [inherits_file_2]}}
    with open(inherits_file_1, "w") as fh:
        yaml.dump(first_order, fh)

    # Base references first order
    base = copy.deepcopy(nested_dict)
    base["a"]["inherits"] = [inherits_file_1]

    # Write base yaml to file
    base_file = os.path.join(tmpdir, "base.yaml")
    with open(base_file, "w") as fh:
        yaml.dump(base, fh)

    # Get target
    target = copy.deepcopy(nested_dict)
    target["a"]["d"] = simple_update["a"]["d"]
    output = load_yaml_with_inheritance(base_file)
    assert output == target

@pytest.mark.parametrize("simple_first", (False, True))
def test_inheritance_sort_order(nested_dict, simple_update, list_update, tmpdir, simple_first):
    inherits_file_simple = os.path.join(tmpdir, "inherits_simple.yaml")
    inherits_file_list = os.path.join(tmpdir, "inherits_file_list.yaml")

    # Write simple inherits file
    with open(inherits_file_simple, "w") as fh:
        yaml.dump(simple_update, fh)

    # Write list inherits file
    with open(inherits_file_list, "w") as fh:
        yaml.dump(list_update, fh)

    base = copy.deepcopy(nested_dict)
    if simple_first:
        inherits = [inherits_file_simple, inherits_file_list]
    else:
        inherits = [inherits_file_list, inherits_file_simple]
    base["a"]["inherits"] = inherits

    # Write base yaml to file
    base_file = os.path.join(tmpdir, "base.yaml")
    with open(base_file, "w") as fh:
        yaml.dump(base, fh)

    # Get target
    target = copy.deepcopy(nested_dict)
    # Later inherits overwrite earlier
    if simple_first:
        target["a"]["d"] = list_update["a"]["d"]
    else:
        target["a"]["d"] = simple_update["a"]["d"]
    output = load_yaml_with_inheritance(base_file)
    assert output == target

