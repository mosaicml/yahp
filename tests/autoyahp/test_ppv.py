import pathlib
from typing import List

import pytest

import yahp as hp
from tests.yahp_fixtures import YamlInput, generate_named_tuple_from_data


@hp.mark_parent_provided_value('int_field')
class InnerClass:

    def __init__(
        self,
        int_field: int,
    ):
        self.int_field = int_field


@hp.create_subclass_registry()
@hp.mark_parent_provided_value('int_field')
class InnerChoiceClass:
    pass


@hp.register_subclass(InnerChoiceClass, 'option_one')
class OptionOneClass:

    def __init__(
        self,
        int_field: int,
        float_field: float,
    ):
        self.int_field = int_field
        self.float_field = float_field


@hp.register_subclass(InnerChoiceClass, 'option_two')
class OptionTwoClass:

    def __init__(
        self,
        int_field: int,
        string_field: str,
    ):
        self.int_field = int_field
        self.string_field = string_field


class PPVClass:

    def __init__(
        self,
        nested_field: InnerClass,
        nested_choice_field: InnerChoiceClass,
        nested_choices_field: List[InnerChoiceClass],
        int_field: int,
    ):
        self.nested_field = nested_field
        self.nested_choice_field = nested_choice_field
        self.nested_choices_field = nested_choices_field
        self.int_field = int_field


@pytest.fixture
def ppv_asset_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data={
                                              "int_field": 7,
                                              "nested_field": {},
                                              "nested_choice_field": {
                                                  "option_one": {
                                                      "float_field": 3.14
                                                  }
                                              },
                                              "nested_choices_field": {
                                                  "option_one": {
                                                      "float_field": 2.718
                                                  },
                                                  "option_two": {
                                                      "string_field": "foobar"
                                                  }
                                              }
                                          },
                                          filepath="ppv_asset.yaml")


def test_ppv_asset_hparams_data(ppv_asset_yaml_input: YamlInput):
    o = hp.create(PPVClass, data=ppv_asset_yaml_input.dict_data)

    assert o.int_field == 7
    assert o.nested_field.int_field == 7

    assert isinstance(o.nested_choice_field, OptionOneClass)
    assert o.nested_choice_field.int_field == 7
    assert o.nested_choice_field.float_field == 3.14

    assert isinstance(o.nested_choices_field[0], OptionOneClass)
    assert o.nested_choices_field[0].int_field == 7
    assert o.nested_choices_field[0].float_field == 2.718

    assert isinstance(o.nested_choices_field[1], OptionTwoClass)
    assert o.nested_choices_field[1].int_field == 7
    assert o.nested_choices_field[1].string_field == "foobar"


def test_ppv_asset_hparams_file(ppv_asset_yaml_input: YamlInput):
    o = hp.create(PPVClass, f=ppv_asset_yaml_input.filename)

    assert o.int_field == 7
    assert o.nested_field.int_field == 7

    assert isinstance(o.nested_choice_field, OptionOneClass)
    assert o.nested_choice_field.int_field == 7
    assert o.nested_choice_field.float_field == 3.14

    assert isinstance(o.nested_choices_field[0], OptionOneClass)
    assert o.nested_choices_field[0].int_field == 7
    assert o.nested_choices_field[0].float_field == 2.718

    assert isinstance(o.nested_choices_field[1], OptionTwoClass)
    assert o.nested_choices_field[1].int_field == 7
    assert o.nested_choices_field[1].string_field == "foobar"


class InnerClassOne:
    pass


@hp.mark_parent_provided_value('inner_one')
class InnerClassTwo:

    def __init__(self, inner_one: InnerClassOne):
        self.inner_one = inner_one


@hp.mark_parent_provided_value('inner_two')
class InnerClassThree:

    def __init__(self, inner_two: InnerClassTwo):
        self.inner_two = inner_two


class NestedPPVClass:

    def __init__(self, inner_one: InnerClassOne, inner_two: InnerClassTwo, inner_three: InnerClassThree):
        self.inner_one = inner_one
        self.inner_two = inner_two
        self.inner_three = inner_three


@pytest.fixture
def nested_ppv_asset_yaml_input(hparams_tempdir: pathlib.Path) -> YamlInput:
    return generate_named_tuple_from_data(hparams_tempdir=hparams_tempdir,
                                          input_data={
                                              "inner_one": {},
                                              "inner_two": {},
                                              "inner_three": {},
                                          },
                                          filepath="nested_ppv_asset.yaml")


def test_nested_ppv_asset_hparams_file(nested_ppv_asset_yaml_input: YamlInput):
    o = hp.create(NestedPPVClass, f=nested_ppv_asset_yaml_input.filename)

    assert o.inner_one is o.inner_two.inner_one
    assert o.inner_two is o.inner_three.inner_two
