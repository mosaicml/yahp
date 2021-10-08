from __future__ import annotations

from enum import Enum
from typing import Dict, List, TypeVar, Union

import yahp as hp

JSON = Union[str, float, int, None, List['JSON'], Dict[str, 'JSON']]

HparamsField = Union[str, float, Enum, hp.Hparams, int, None, List[hp.Hparams], List[str], List[float], List[int],
                     List[Enum], Dict[str, JSON], List[Union[str, float]], List[Union[str, int]],]

THparams = TypeVar("THparams", bound=hp.Hparams)
