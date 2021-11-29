# Copyright 2021 MosaicML. All Rights Reserved.

import pytest

from tests.yahp_fixtures import FloatToBoolFixture, PrimitiveHparam, YamlInput


def test_primitive_hparams_create(primitive_yaml_input: YamlInput):
    PrimitiveHparam.create(data=primitive_yaml_input.dict_data, cli_args=[])


def test_primitive_hparams_create_fail_with_extra_parameter(primitive_yaml_input: YamlInput):
    input_dict = primitive_yaml_input.dict_data
    input_dict["extra_random_parameter"] = 42
    with pytest.raises(Exception):
        PrimitiveHparam.create(data=input_dict, cli_args=[])


def test_primitive_hparams_field_types(primitive_hparam: PrimitiveHparam):
    primitive_hparam.validate()


def test_primitive_hparams_enum(primitive_yaml_input: YamlInput):
    data = primitive_yaml_input.dict_data
    data["enumintfield"] = 1
    PrimitiveHparam.create(data=data, cli_args=[])
    data["enumintfield"] = "ONE"
    PrimitiveHparam.create(data=data, cli_args=[])
    with pytest.raises(Exception):
        # TODO: Determine if '1' should fail
        data["enumintfield"] = "1"
        PrimitiveHparam.create(data=data, cli_args=[])
        data["enumintfield"] = "TWELVE"
        PrimitiveHparam.create(data=data, cli_args=[])
        data["enumintfield"] = 12
        PrimitiveHparam.create(data=data, cli_args=[])
    data["enumintfield"] = 1
    data["enumstringfield"] = "ptl"
    PrimitiveHparam.create(data=data, cli_args=[])
    data["enumstringfield"] = "PYTORCH_LIGHTNING"
    PrimitiveHparam.create(data=data, cli_args=[])
    with pytest.raises(Exception):
        data["enumstringfield"] = 12
        PrimitiveHparam.create(data=data, cli_args=[])
        data["enumstringfield"] = "MISSPELLING"
        PrimitiveHparam.create(data=data, cli_args=[])


def test_primitive_hparams_field_failure(primitive_hparam: PrimitiveHparam):
    primitive_hparam.intfield = "asdf"  # type: ignore
    with pytest.raises(Exception):
        primitive_hparam.validate()


def test_primitive_hparams_create_from_file(primitive_yaml_input: YamlInput):
    return PrimitiveHparam.create(f=primitive_yaml_input.filename, cli_args=[])


def test_primitive_hparams_create_from_instance_dump(primitive_hparam: PrimitiveHparam):
    dump = primitive_hparam.to_dict()
    PrimitiveHparam.create(data=dump, cli_args=[])


def test_primitive_hparams_json(primitive_hparam: PrimitiveHparam):
    assert isinstance(primitive_hparam.jsonfield, dict)
    assert isinstance(primitive_hparam.jsonfield["random_item"], int)
    assert isinstance(primitive_hparam.jsonfield["random_item2"], str)
    assert isinstance(primitive_hparam.jsonfield["random_item3"], bool)
    assert isinstance(primitive_hparam.jsonfield["random_item4"], float)


def test_load_and_convert_defaults():
    hparams = FloatToBoolFixture.create(cli_args=[])
    assert isinstance(hparams.float_field, float)
    assert hparams.float_field == 1.0
