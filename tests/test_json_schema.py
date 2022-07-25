import contextlib
import json
import os
import pathlib
import textwrap
from typing import Type

import pytest
import yaml
from jsonschema import ValidationError

from tests.yahp_fixtures import (BearsHparams, ChoiceHparamParent, KitchenSinkHparams, PrimitiveHparam,
                                 ShavingBearsHparam)
from yahp.hparams import Hparams


@pytest.mark.parametrize('hparam_class,success,data', [
    [
        PrimitiveHparam, True,
        textwrap.dedent("""
            ---
            intfield: 1
            strfield: hello
            floatfield: 0.5
            boolfield: true
            enumintfield: ONE
            enumstringfield: mosaic
            jsonfield:
                empty_item: {}
                random_item: 1
                random_item2: two
                random_item3: true
                random_item4: 0.1
                random_subdict:
                    random_subdict_item5: 12
                    random_subdict_item6: 1337
                random_list:
                    - 1
                    - 3
                    - 99
                random_list_of_dict:
                    - sub_dict: 12
                      sub_dict_item: 1
                    - sub_dict2: 14
                      sub_dict_item: 43
        """)
    ],
    [
        PrimitiveHparam, False,
        textwrap.dedent("""
            ---
            strfield: hello
            floatfield: 0.5
            boolfield: true
            enumintfield: ONE
            enumstringfield: mosaic
            jsonfield:
                empty_item: {}
                random_item: 1
                random_item2: two
                random_item3: true
                random_item4: 0.1
                random_subdict:
                    random_subdict_item5: 12
                    random_subdict_item6: 1337
                random_list:
                    - 1
                    - 3
                    - 99
                random_list_of_dict:
                    - sub_dict: 12
                      sub_dict_item: 1
                    - sub_dict2: 14
                      sub_dict_item: 43
        """)
    ],
    [
        KitchenSinkHparams,
        True,
        textwrap.dedent("""
            ---
            required_int_field: 1
            nullable_required_int_field:
            required_bool_field: False
            nullable_required_bool_field:
            required_enum_field_list:
                - RED
                - red
            required_enum_field_with_default: green
            nullable_required_enum_field: None
            nullable_required_enum_field:
            required_union_bool_str_field: hi
            nullable_required_union_bool_str_field:
            required_int_list_field:
                - 1
                - 2
                - 42
            nullable_required_list_int_field:
                - 24
            nullable_required_list_union_bool_str_field:
            required_list_union_bool_str_field:
                - True
                - hi
                - False
                - bye
            required_subhparams_field: { default_false: False, default_true: True }
            nullable_required_subhparams_field:
            required_subhparams_field_list:
                - { default_false: False }
                - {}
            nullable_required_subhparams_field_list:
            required_choice:
                one:
                    commonfield: True
                    intfield: 3
            nullable_required_choice:
            required_choice_list: []
            nullable_required_choice_list:
            optional_float_field_default_1: 1.1
        """),
    ],
    [ChoiceHparamParent, True,
     textwrap.dedent("""
            ---
            commonfield: True
        """)],
    [ChoiceHparamParent, False,
     textwrap.dedent("""
            ---
            commonfield: 1
        """)],
    [
        ShavingBearsHparam, True,
        textwrap.dedent("""
            ---
            parameters:
                random_field:
                shaved_bears:
                    first_action: "Procure bears"
                    last_action: "Release bears into wild with stylish new haircuts"
                other_random_field: "cool"
        """)
    ],
    [BearsHparams, True, textwrap.dedent("""
            ---
            bears:
        """)],
    [
        BearsHparams, True,
        textwrap.dedent("""
            ---
            bears:
                - shaved_bears:
                    first_action: "Procure bears"
                    last_action: "Release bears into wild with stylish new haircuts"
        """)
    ],
    [
        BearsHparams, True,
        textwrap.dedent("""
            ---
            bears:
                - unshaved_bears:
                    second_action: "Procure bears"
                    third_action: "Release bears into wild with stylish new haircuts"
        """)
    ],
    [
        BearsHparams, True,
        textwrap.dedent("""
            ---
            bears:
                - shaved_bears:
                    first_action: "Procure bears"
                    last_action: "Release bears into wild with stylish new haircuts"
                - unshaved_bears:
                    second_action: "Procure bears"
                    third_action: "Release bears into wild with stylish new haircuts"
        """)
    ],
    [
        BearsHparams, True,
        textwrap.dedent("""
            ---
            bears:
                - shaved_bears+first:
                    first_action: "Procure bears"
                    last_action: "Release bears into wild with stylish new haircuts"
                - shaved_bears+second:
                    first_action: "Procure bears"
                    last_action: "Release bears into wild with stylish new haircuts"
        """)
    ],
])
def test_validate_json_schema_from_strings(hparam_class: Type[Hparams], success: bool, data: str):
    with contextlib.nullcontext() if success else pytest.raises(ValidationError):
        hparam_class.validate_yaml(data=yaml.safe_load(data))


@pytest.mark.parametrize('hparam_class,success,file', [
    [ShavingBearsHparam, True,
     os.path.join(os.path.dirname(__file__), 'inheritance/shaving_bears.yaml')],
])
def test_validate_json_schema_from_file(hparam_class: Type[Hparams], success: bool, file: str):
    with contextlib.nullcontext() if success else pytest.raises(ValidationError):
        hparam_class.validate_yaml(f=file)


@pytest.mark.parametrize('hparam_class', [
    ShavingBearsHparam,
    ChoiceHparamParent,
    PrimitiveHparam,
    KitchenSinkHparams,
    BearsHparams,
])
def test_write_and_read_json_schema_from_name(hparam_class: Type[Hparams], tmp_path: pathlib.Path):
    file = os.path.join(tmp_path, 'schema.json')
    hparam_class.dump_jsonschema(file)
    with open(file) as f:
        loaded_schema = json.load(f)
    generated_schema = hparam_class.get_json_schema()
    assert loaded_schema == generated_schema


@pytest.mark.parametrize('hparam_class', [
    ShavingBearsHparam,
    ChoiceHparamParent,
    PrimitiveHparam,
    KitchenSinkHparams,
    BearsHparams,
])
def test_write_and_read_json_schema_from_file(hparam_class: Type[Hparams], tmp_path: pathlib.Path):
    file = os.path.join(tmp_path, 'schema.json')
    with open(file, 'w') as f:
        hparam_class.dump_jsonschema(f)
    with open(file) as f:
        loaded_schema = json.load(f)
    generated_schema = hparam_class.get_json_schema()
    assert loaded_schema == generated_schema
