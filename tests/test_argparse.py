# Copyright 2021 MosaicML. All Rights Reserved.

import pytest

from tests.yahp_fixtures import (ListHparam, OptionalBooleansHparam, YamlInput, OptionalRequiredParentHparam)


def test_boolean_overrides_explicit(empty_object_yaml_input: YamlInput):
    o = OptionalBooleansHparam.create(
        cli_args=['-f', empty_object_yaml_input.filename, '--default_true', 'false', '--default_false', 'true'])
    assert o.default_true == False
    assert o.default_false == True


def test_boolean_overrides_implicit(empty_object_yaml_input: YamlInput):
    o = OptionalBooleansHparam.create(
        cli_args=['-f', empty_object_yaml_input.filename, '--default_true', '--default_false'])
    assert o.default_true == True
    assert o.default_false == True


def test_list_hparam(empty_object_yaml_input: YamlInput):
    o = ListHparam.create(cli_args=['-f', empty_object_yaml_input.filename, '--list_of_str', 'one', 'two'],)
    assert isinstance(o.list_of_str, list)
    assert isinstance(o.list_of_str[0], str)
    assert len(o.list_of_str) == 2
    assert len(o.list_of_int) == 0
    assert o.list_of_str[0] == "one"
    assert isinstance(o.list_of_str[1], str)
    assert o.list_of_str[1] == "two"


def test_list_hparam_int(empty_object_yaml_input: YamlInput):
    o = ListHparam.create(cli_args=['-f', empty_object_yaml_input.filename, '--list_of_int', '1', '2'])
    assert isinstance(o.list_of_int, list)
    assert isinstance(o.list_of_int[0], int)
    assert o.list_of_int[0] == 1
    assert isinstance(o.list_of_int[1], int)
    assert o.list_of_int[1] == 2


def test_list_hparam_bool(empty_object_yaml_input: YamlInput):
    o = ListHparam.create(cli_args=['-f', empty_object_yaml_input.filename, '--list_of_bool', 'true', 'false'])
    assert isinstance(o.list_of_bool, list)
    assert isinstance(o.list_of_bool[0], bool)
    assert o.list_of_bool[0] == True
    assert isinstance(o.list_of_bool[1], bool)
    assert o.list_of_bool[1] == False


def test_get_helpless_argpars():
    args = ['--default_true', 'false', '--default_false', 'true']
    parser = OptionalBooleansHparam.get_argparse(cli_args=args)
    namespace = parser.parse_args(args)
    assert namespace.default_true == 'false'
    assert namespace.default_false == 'true'
    with pytest.raises(SystemExit):
        parser.parse_args("--help")


def test_optional_required_hparams_only_child():
    args = ['--optional_child.required_field', '5']
    o = OptionalRequiredParentHparam.create(cli_args=args)
    assert o.optional_child is not None
    assert o.optional_child.required_field == 5


def test_optional_required_hparams_both():
    args = ['--optional_child', '5', '--optional_child.required_field', '5']
    o = OptionalRequiredParentHparam.create(cli_args=args)
    assert o.optional_child is not None
    assert o.optional_child.required_field == 5
