import pathlib
from typing import List, Optional

import pytest

import yahp as hp
from tests.yahp_fixtures import YamlInput, generate_named_tuple_from_data


class InnerClass:

    def __init__(
        self,
        int_field: int,
    ):
        self.int_field = int_field


class NestedAssetsClass:

    def __init__(
        self,
        nested_field: InnerClass,
        optional_nested_field: Optional[InnerClass],
    ):
        self.nested_field = nested_field
        self.optional_nested_field = optional_nested_field


@pytest.fixture
def nested_asset_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data={
                                              "nested_field": {
                                                  "int_field": 1
                                              },
                                          },
                                          filepath="nested_asset.yaml")


def test_nested_asset_hparams_data(nested_asset_yaml_input: YamlInput):
    o = hp.create(NestedAssetsClass, data=nested_asset_yaml_input.dict_data)

    assert isinstance(o.nested_field, InnerClass)
    assert o.nested_field.int_field == 1
    assert o.optional_nested_field == None


def test_nested_asset_hparams_file(nested_asset_yaml_input: YamlInput):
    o = hp.create(NestedAssetsClass, f=nested_asset_yaml_input.filename)

    assert isinstance(o.nested_field, InnerClass)
    assert o.nested_field.int_field == 1
    assert o.optional_nested_field == None


@hp.create_subclass_registry()
class ChoiceClass:
    pass


class OptionOneClass(ChoiceClass, canonical_name="option_one"):

    def __init__(self, int_field: int):
        self.int_field = int_field


class OptionTwoClass(ChoiceClass, canonical_name="option_two"):

    def __init__(self, string_field: str):
        self.string_field = string_field


class NestedChoiceAssetClass:

    def __init__(
        self,
        nested_field: ChoiceClass,
        nested_fields: List[ChoiceClass],
        optional_nested_field: Optional[ChoiceClass],
    ):
        self.nested_field = nested_field
        self.nested_fields = nested_fields
        self.optional_nested_field = optional_nested_field


@pytest.fixture
def nested_choice_asset_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data={
                                              "nested_field": {
                                                  "option_one": {
                                                      "int_field": 1
                                                  }
                                              },
                                              "nested_fields": {
                                                  "option_one": {
                                                      "int_field": 2
                                                  },
                                                  "option_two": {
                                                      "string_field": 'foobar'
                                                  }
                                              }
                                          },
                                          filepath="nested_choice_asset.yaml")


def test_nested_choice_asset_hparams_data(nested_choice_asset_yaml_input: YamlInput):
    o = hp.create(NestedChoiceAssetClass, data=nested_choice_asset_yaml_input.dict_data)

    assert isinstance(o.nested_field, ChoiceClass)
    assert isinstance(o.nested_fields[0], OptionOneClass)
    assert isinstance(o.nested_fields[1], OptionTwoClass)
    assert o.nested_field.int_field == 1
    assert o.nested_fields[0].int_field == 2
    assert o.nested_fields[1].string_field == 'foobar'
    assert o.optional_nested_field == None


def test_nested_choice_asset_hparams_file(nested_choice_asset_yaml_input: YamlInput):
    o = hp.create(NestedChoiceAssetClass, f=nested_choice_asset_yaml_input.filename)

    assert isinstance(o.nested_field, ChoiceClass)
    assert isinstance(o.nested_fields[0], OptionOneClass)
    assert isinstance(o.nested_fields[1], OptionTwoClass)
    assert o.nested_field.int_field == 1
    assert o.nested_fields[0].int_field == 2
    assert o.nested_fields[1].string_field == 'foobar'
    assert o.optional_nested_field == None
