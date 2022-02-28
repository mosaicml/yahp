# Copyright 2021 MosaicML. All Rights Reserved.

from typing import Dict

import pytest

from tests.yahp_fixtures import ChoiceHparamRoot, ChoiceOneHparam, EmptyHparam, NestedHparam, PrimitiveHparam, YamlInput
from yahp.types import JSON


def test_register_new_hparam_choice(choice_one_yaml_input: YamlInput):
    # Should fail because directly nested hparams can't be over-registered
    ChoiceHparamRoot.register_class(
        field="choice",
        register_class=EmptyHparam,
        class_key="empty",
    )

    root_hparams_data: Dict[str, JSON] = {"choice": {"one": choice_one_yaml_input.dict_data}}

    choice_one_hparam = ChoiceHparamRoot.create(data=root_hparams_data)
    # Check that existing hparams still work
    assert isinstance(choice_one_hparam.choice, ChoiceOneHparam)

    # Check that new registered hparams can be created
    root_hparams_data["choice"] = {"empty": None}
    choice_empty = ChoiceHparamRoot.create(data=root_hparams_data)

    assert isinstance(choice_empty.choice, EmptyHparam)


def test_register_new_hparam_direct(nested_hparams: NestedHparam):
    # Should fail because directly nested hparams can't be over-registered
    with pytest.raises(ValueError):
        nested_hparams.register_class(
            field="primitive_hparam",
            register_class=EmptyHparam,
            class_key="empty",
        )


def test_register_non_existing(nested_hparams: NestedHparam):
    # Tries to register for a nonexisting field
    with pytest.raises(ValueError):
        nested_hparams.register_class(
            field="nonexisting_hparam",
            register_class=EmptyHparam,
            class_key="empty",
        )


def test_register_existing_primative():
    # Tries to register for a nonexisting field
    with pytest.raises(ValueError):
        PrimitiveHparam.register_class(
            field="intfield",
            register_class=EmptyHparam,
            class_key="empty",
        )
