# Copyright 2021 MosaicML. All Rights Reserved.

import pytest

from tests.yahp_fixtures import ChoiceHparamRoot, ChoiceOneHparam, ChoiceThreeHparam, ChoiceTwoHparam, YamlInput


def test_create_choice_one_hparams_data_root(choice_one_yaml_input: YamlInput):
    ChoiceHparamRoot.create(data={
        'choice': {
            'one': choice_one_yaml_input.dict_data
        },
    })


def test_create_choice_one_hparams_data(choice_one_yaml_input: YamlInput):
    ChoiceOneHparam.create(data=choice_one_yaml_input.dict_data)


def test_create_choice_one_hparams_file(choice_one_yaml_input: YamlInput):
    ChoiceOneHparam.create(f=choice_one_yaml_input.filename)


def test_create_choice_two_hparams_data_root(choice_two_yaml_input: YamlInput):
    ChoiceHparamRoot.create(data={
        'choice': {
            'two': choice_two_yaml_input.dict_data
        },
    })


def test_create_choice_two_hparams_data(choice_two_yaml_input: YamlInput):
    ChoiceTwoHparam.create(data=choice_two_yaml_input.dict_data)


def test_create_choice_two_hparams_file(choice_two_yaml_input: YamlInput):
    ChoiceTwoHparam.create(f=choice_two_yaml_input.filename)


def test_create_choice_three_one_hparams_data_root(choice_three_one_yaml_input: YamlInput):
    ChoiceHparamRoot.create(data={
        'choice': {
            'three': choice_three_one_yaml_input.dict_data
        },
    })


def test_create_choice_three_one_hparams_data(choice_three_one_yaml_input: YamlInput):
    ChoiceThreeHparam.create(data=choice_three_one_yaml_input.dict_data)


def test_create_choice_three_one_hparams_data_fail_with_incorrect_nested_data(choice_three_one_yaml_input: YamlInput):
    data = choice_three_one_yaml_input.dict_data
    data['choice']['one']['commonfield'] = 12
    with pytest.raises(Exception):
        ChoiceThreeHparam.create(data=data)


def test_create_choice_three_one_hparams_data_fail_with_missing_nested_data(choice_three_one_yaml_input: YamlInput):
    data = choice_three_one_yaml_input.dict_data
    del data['choice']['one']['commonfield']
    with pytest.raises(Exception):
        ChoiceThreeHparam.create(data=data)


def test_create_choice_three_one_hparams_file(choice_three_one_yaml_input: YamlInput):
    ChoiceThreeHparam.create(f=choice_three_one_yaml_input.filename)


def test_create_choice_three_two_hparams_data_root(choice_three_two_yaml_input: YamlInput):
    ChoiceHparamRoot.create(data={
        'choice': {
            'three': choice_three_two_yaml_input.dict_data
        },
    })


def test_create_choice_three_two_hparams_data(choice_three_two_yaml_input: YamlInput):
    ChoiceThreeHparam.create(data=choice_three_two_yaml_input.dict_data)


def test_create_choice_three_two_hparams_file(choice_three_two_yaml_input: YamlInput):
    ChoiceThreeHparam.create(f=choice_three_two_yaml_input.filename)


def test_create_choice_three_two_hparams_data_fail_with_incorrect_double_nested_data(
        choice_three_two_yaml_input: YamlInput):
    data = choice_three_two_yaml_input.dict_data
    data['choice']['two']['primitive_hparam']['intfield'] = 'hello'
    with pytest.raises(Exception):
        ChoiceThreeHparam.create(data=data)


def test_create_choice_three_two_hparams_data_fail_with_missing_double_nested_data(
        choice_three_two_yaml_input: YamlInput):
    data = choice_three_two_yaml_input.dict_data
    del data['choice']['two']['primitive_hparam']['boolfield']
    with pytest.raises(Exception):
        ChoiceThreeHparam.create(data=data)


def test_choice_three_two_recreation_from_instance_dump(choice_three_two_hparam: ChoiceThreeHparam):
    dump = choice_three_two_hparam.to_dict()
    ChoiceThreeHparam.create(data=dump)
