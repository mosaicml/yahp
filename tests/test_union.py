# Copyright 2021 MosaicML. All Rights Reserved.

from dataclasses import dataclass
from typing import Union

import pytest

import yahp as hp


@pytest.mark.parametrize('val,expected', [('1', '1'), ('1ep', '1ep'), (2, 2)])
def test_union(val: Union[str, int], expected: Union[str, int]):

    @dataclass
    class HparamsWithUnion(hp.Hparams):
        union_field: Union[str, int] = hp.required('time')

    hparams = HparamsWithUnion.create(data={'union_field': val})
    assert isinstance(hparams, HparamsWithUnion)
    assert hparams.union_field == expected
