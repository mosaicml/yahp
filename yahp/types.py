from __future__ import annotations

from enum import Enum
from typing import Dict, List, Tuple, TypeVar, Union

import yahp as hp

JSON = Union[str, float, int, None, List['JSON'], Dict[str, 'JSON']]

# str is a valid Sequence[str], so manually enumerating the types a collection of strings
SequenceStr = Union[List[str], Tuple[str, ...]]

TPrimitiveHparams = Union[str, float, None, int, bool, Enum, hp.Hparams]
# We explicitely do not allow lists of mixed types
# For compatibility with third-party libraries we allow Dict[str, JSON]
THparams = Union[TPrimitiveHparams, List[str], List[float], List[int], List[Enum], List[hp.Hparams], Dict[str, JSON]]
THparamsSubclass = TypeVar("THparamsSubclass", bound=hp.Hparams)
