import os
import textwrap
from typing import Type

import pytest
from jsonschema import ValidationError

from tests.yahp_fixtures import ChoiceHparamParent, PrimitiveHparam, ShavingBearsHparam
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
            enumstringfield: pytorch_lightning
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
            enumstringfield: pytorch_lightning
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
])
def test_validate_json_schema_from_data(hparam_class: Type[Hparams], success: bool, data: str):
    if success:
        hparam_class.validate_yaml(data=data)
    else:
        with pytest.raises(ValidationError):
            hparam_class.validate_yaml(data=data)


@pytest.mark.parametrize('hparam_class,success,file', [
    [ShavingBearsHparam, True,
     os.path.join(os.path.dirname(__file__), 'inheritance/shaving_bears.yaml')],
])
def test_validate_json_schema_from_file2(hparam_class: Type[Hparams], success: bool, file: str):
    if success:
        hparam_class.validate_yaml(f=file)
    else:
        with pytest.raises(ValidationError):
            hparam_class.validate_yaml(f=file)
