from __future__ import annotations

from enum import Enum
from typing import Dict, List, Tuple, TypeVar, Union

import yahp as hp

JSON = Union[str, float, int, None, List['JSON'], Dict[str, 'JSON']]

SequenceStr = Union[List[str], Tuple[str, ...]]
"""SequenceStr represents a List[str] or Tuple[str].
Sequence[str] is not used as a :class:`str` is a valid `Sequence[str]`, which is usually unintended."""

HparamsField = Union[str, float, Enum, hp.Hparams, int, None, List[hp.Hparams], List[str], List[float], List[int],
                     List[Enum], Dict[str, JSON], List[Union[str, float]], List[Union[str, int]],]

THparams = TypeVar("THparams", bound=hp.Hparams)
