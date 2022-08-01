import contextlib
import textwrap
from typing import Type

import pytest
import yaml

from tests.yahp_fixtures import HairyBearsHparams
from yahp.hparams import Hparams


@pytest.mark.parametrize('hparam_class,success,data', [
    [
        HairyBearsHparams, True,
        textwrap.dedent("""
            ---
            bears:
                - second_action: "Procure bears"
                  third_action: "Release bears into wild with stylish new haircuts"
                - second_action: "Procure bears"
                  third_action: "Release bears into wild with stylish new haircuts"
        """)
    ],
    [
        HairyBearsHparams, False,
        textwrap.dedent("""
            ---
            bears:
                - bear:
                    second_action: "Procure bears"
                    third_action: "Release bears into wild with stylish new haircuts"
                - hairybear:
                    second_action: "Procure bears"
                    third_action: "Release bears into wild with stylish new haircuts"
        """)
    ],
])
def test_create_yaml_with_phantom_keys(hparam_class: Type[Hparams], success: bool, data: str):
    with contextlib.nullcontext() if success else pytest.raises(DeprecationWarning):
        hparam_class.create(data=yaml.safe_load(data))
