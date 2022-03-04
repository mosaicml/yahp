# Copyright 2021 MosaicML. All Rights Reserved.

from enum import Enum
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Type, Union

import pytest

from yahp.utils.type_helpers import HparamsType, _JSONDict


class TypeHelperFixture(NamedTuple):
    t: Type
    is_optional: bool
    is_list: bool
    types: Sequence[Type[Any]]


@pytest.mark.parametrize('fixture', [
    TypeHelperFixture(t=None, is_optional=True, is_list=False, types=[]),
    TypeHelperFixture(t=Optional[int], is_optional=True, is_list=False, types=[int]),
    TypeHelperFixture(t=List[int], is_optional=False, is_list=True, types=[int]),
    TypeHelperFixture(t=Union[int, str], is_optional=False, is_list=False, types=[int, str]),
    TypeHelperFixture(t=List[Union[int, str]], is_optional=False, is_list=True, types=[int, str]),
    TypeHelperFixture(t=Optional[List[Union[int, str]]], is_optional=True, is_list=True, types=[int, str]),
    TypeHelperFixture(t=Optional[Enum], is_optional=True, is_list=False, types=[Enum]),
    TypeHelperFixture(t=Optional[List[Enum]], is_optional=True, is_list=True, types=[Enum]),
    TypeHelperFixture(t=Dict[str, Any], is_optional=False, is_list=False, types=[_JSONDict])
])
def test_type_helper(fixture: TypeHelperFixture):
    hparams_type = HparamsType(fixture.t)
    assert hparams_type.is_list == fixture.is_list
    assert hparams_type.is_optional == fixture.is_optional
    assert set(hparams_type.types) == set(fixture.types)
