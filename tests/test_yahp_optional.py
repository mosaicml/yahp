# Copyright 2021 MosaicML. All Rights Reserved.

from tests.yahp_fixtures import OptionalBooleansHparam, OptionalFieldHparam, OptionalHparamsField, YamlInput


def test_empty_object_optional_field_hparams_data(optional_field_empty_object_yaml_input: YamlInput):
    o = OptionalFieldHparam.create(data=optional_field_empty_object_yaml_input.dict_data, cli_args=[])
    assert o.choice.maybe == 0


def test_empty_object_optional_field_hparams_file(optional_field_empty_object_yaml_input: YamlInput):
    o = OptionalFieldHparam.create(f=optional_field_empty_object_yaml_input.filename, cli_args=[])
    assert o.choice.maybe == 0


def test_null_object_optional_field_hparams_data(optional_field_null_object_yaml_input: YamlInput):
    o = OptionalFieldHparam.create(data=optional_field_null_object_yaml_input.dict_data, cli_args=[])
    assert o.choice.maybe == 0


def test_null_object_optional_field_hparams_file(optional_field_null_object_yaml_input: YamlInput):
    o = OptionalFieldHparam.create(f=optional_field_null_object_yaml_input.filename, cli_args=[])
    assert o.choice.maybe == 0


def test_optional_hparams_field():
    o = OptionalHparamsField()
    assert o.optional_hparams is None


def test_optional_booleans_hparams_data(empty_object_yaml_input: YamlInput):
    o = OptionalBooleansHparam.create(data=empty_object_yaml_input.dict_data, cli_args=[])
    assert o.default_true
    assert not o.default_false


def test_optional_booleans_hparams_file(empty_object_yaml_input: YamlInput):
    o = OptionalBooleansHparam.create(f=empty_object_yaml_input.filename, cli_args=[])
    assert o.default_true
    assert not o.default_false
