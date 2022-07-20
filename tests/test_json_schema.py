import os
import pytest
import textwrap
import tempfile
from typing import Type
from jsonschema import ValidationError
import json

from tests.yahp_fixtures import PrimitiveHparam, ChoiceHparamParent, ShavingBearsHparam

from yahp.hparams import Hparams

@pytest.mark.parametrize('hparam_class,success,data', 
    [
        [PrimitiveHparam, True, textwrap.dedent("""
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
        """)],
        [PrimitiveHparam, False, textwrap.dedent("""
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
        """)],
        [ChoiceHparamParent, True, textwrap.dedent("""
            ---
            commonfield: True
        """)],
        [ChoiceHparamParent, False, textwrap.dedent("""
            ---
            commonfield: 1
        """)],
    ]
)
def test_validate_json_schema_from_data(hparam_class: Type[Hparams], success: bool, data: str):
    if success:
        hparam_class.validate_yaml(data=data)
    else:
        with pytest.raises(ValidationError):
            hparam_class.validate_yaml(data=data)

@pytest.mark.parametrize('hparam_class,success', 
    [
        [ShavingBearsHparam, True],
    ]
)
def test_validate_json_schema_from_file(hparam_class: Type[Hparams], success: bool):
    print(json.dumps(hparam_class.get_json_schema(), sort_keys=False, indent=4))
    with tempfile.TemporaryDirectory() as tmpdirname:
        shaving_bears = textwrap.dedent("""
        ---
        parameters:
            random_field: 12
            shaved_bears:
                first_action: "Procure bears"
                last_action: "Release bears into wild with stylish new haircuts"
            other_random_field: "cool"
        """)
        filename = os.path.join(tmpdirname, "shaving_bears.yaml")
        with open(filename, 'w') as f:
            f.write(shaving_bears)
        if success:
            hparam_class.validate_yaml(f=filename)
        else:
            with pytest.raises(ValidationError):
                hparam_class.validate_yaml(f=filename)