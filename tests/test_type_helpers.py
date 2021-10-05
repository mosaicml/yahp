from enum import Enum
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Type, Union

import pytest

from yahp.type_helpers import HparamsType, _JSONDict


class TestEnum(Enum):
    pass


class TestFixture(NamedTuple):
    t: Type
    is_optional: bool
    is_list: bool
    types: Sequence[Type[Any]]


@pytest.mark.parametrize("fixture", [
    TestFixture(t=None, is_optional=True, is_list=False, types=[]),
    TestFixture(t=Optional[int], is_optional=True, is_list=False, types=[int]),
    TestFixture(t=List[int], is_optional=False, is_list=True, types=[int]),
    TestFixture(t=Union[int, str], is_optional=False, is_list=False, types=[int, str]),
    TestFixture(t=List[Union[int, str]], is_optional=False, is_list=True, types=[int, str]),
    TestFixture(t=Optional[List[Union[int, str]]], is_optional=True, is_list=True, types=[int, str]),
    TestFixture(t=Optional[Enum], is_optional=True, is_list=False, types=[Enum]),
    TestFixture(t=Optional[List[Enum]], is_optional=True, is_list=True, types=[Enum]),
    TestFixture(t=Dict[str, Any], is_optional=False, is_list=False, types=[_JSONDict])
])
def test_type_helper(fixture: TestFixture):
    hparams_type = HparamsType(fixture.t)
    assert hparams_type.is_list == fixture.is_list
    assert hparams_type.is_optional == fixture.is_optional
    assert set(hparams_type.types) == set(fixture.types)
