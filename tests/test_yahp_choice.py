import pytest

from tests.yahp_fixtures import ChoiceHparamRoot, ChoiceOneHparam, ChoiceThreeHparam, ChoiceTwoHparam, YamlInput


def test_create_choice_one_hparams_data_root(choice_one_yaml_input: YamlInput):
    ChoiceHparamRoot.create_from_dict(data={
        "choice": {
            "one": choice_one_yaml_input.dict_data
        },
    })


def test_create_choice_one_hparams_data(choice_one_yaml_input: YamlInput):
    ChoiceOneHparam.create_from_dict(data=choice_one_yaml_input.dict_data)


def test_create_choice_one_hparams_file(choice_one_yaml_input: YamlInput):
    ChoiceOneHparam.create(filepath=choice_one_yaml_input.filename)


def test_create_choice_two_hparams_data_root(choice_two_yaml_input: YamlInput):
    ChoiceHparamRoot.create_from_dict(data={
        "choice": {
            "two": choice_two_yaml_input.dict_data
        },
    })


def test_create_choice_two_hparams_data(choice_two_yaml_input: YamlInput):
    ChoiceTwoHparam.create_from_dict(data=choice_two_yaml_input.dict_data)


def test_create_choice_two_hparams_file(choice_two_yaml_input: YamlInput):
    ChoiceTwoHparam.create(filepath=choice_two_yaml_input.filename)


def test_create_choice_three_one_hparams_data_root(choice_three_one_yaml_input: YamlInput):
    ChoiceHparamRoot.create_from_dict(data={
        "choice": {
            "three": choice_three_one_yaml_input.dict_data
        },
    })


def test_create_choice_three_one_hparams_data(choice_three_one_yaml_input: YamlInput):
    ChoiceThreeHparam.create_from_dict(data=choice_three_one_yaml_input.dict_data)


def test_create_choice_three_one_hparams_data_fail_with_incorrect_nested_data(choice_three_one_yaml_input: YamlInput):
    data = choice_three_one_yaml_input.dict_data
    data["choice"]["one"]["commonfield"] = 12
    with pytest.raises(Exception):
        ChoiceThreeHparam.create_from_dict(data=data)


def test_create_choice_three_one_hparams_data_fail_with_missing_nested_data(choice_three_one_yaml_input: YamlInput):
    data = choice_three_one_yaml_input.dict_data
    del data["choice"]["one"]["commonfield"]
    with pytest.raises(Exception):
        ChoiceThreeHparam.create_from_dict(data=data)


def test_create_choice_three_one_hparams_file(choice_three_one_yaml_input: YamlInput):
    ChoiceThreeHparam.create(filepath=choice_three_one_yaml_input.filename)


def test_create_choice_three_two_hparams_data_root(choice_three_two_yaml_input: YamlInput):
    ChoiceHparamRoot.create_from_dict(data={
        "choice": {
            "three": choice_three_two_yaml_input.dict_data
        },
    })


def test_create_choice_three_two_hparams_data(choice_three_two_yaml_input: YamlInput):
    ChoiceThreeHparam.create_from_dict(data=choice_three_two_yaml_input.dict_data)


def test_create_choice_three_two_hparams_file(choice_three_two_yaml_input: YamlInput):
    ChoiceThreeHparam.create(filepath=choice_three_two_yaml_input.filename)


def test_create_choice_three_two_hparams_data_fail_with_incorrect_double_nested_data(
        choice_three_two_yaml_input: YamlInput):
    data = choice_three_two_yaml_input.dict_data
    data["choice"]["two"]["primitive_hparam"]["intfield"] = "hello"
    with pytest.raises(Exception):
        ChoiceThreeHparam.create_from_dict(data=data)


def test_create_choice_three_two_hparams_data_fail_with_missing_double_nested_data(
        choice_three_two_yaml_input: YamlInput):
    data = choice_three_two_yaml_input.dict_data
    del data["choice"]["two"]["primitive_hparam"]["boolfield"]
    with pytest.raises(Exception):
        ChoiceThreeHparam.create_from_dict(data=data)


def test_choice_three_two_recreation_from_instance_dump(choice_three_two_hparam: ChoiceThreeHparam):
    dump = choice_three_two_hparam.to_dict()
    ChoiceThreeHparam.create_from_dict(data=dump)
