# Copyright 2021 MosaicML. All Rights Reserved.

from tests.yahp_fixtures import DoubleNestedHparam, NestedHparam, YamlInput


def test_direct_nested_create(nested_yaml_input: YamlInput):
    NestedHparam.create(data=nested_yaml_input.dict_data, cli_args=[])


def test_direct_nested_create_from_file(nested_yaml_input: YamlInput):
    NestedHparam.create(f=nested_yaml_input.filename, cli_args=[])


def test_direct_nested_field_types(nested_hparams: NestedHparam):
    nested_hparams.validate()


def test_double_nested_create(double_nested_yaml_input: YamlInput):
    DoubleNestedHparam.create(data=double_nested_yaml_input.dict_data, cli_args=[])


def test_double_nested_create_from_file(double_nested_yaml_input: YamlInput):
    DoubleNestedHparam.create(f=double_nested_yaml_input.filename, cli_args=[])


def test_double_nested_field_types(double_nested_hparams: DoubleNestedHparam):
    double_nested_hparams.validate()
