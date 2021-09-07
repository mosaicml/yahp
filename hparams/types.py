from enum import Enum
from typing import Dict, List, Union

JSON = Union[str, float, int, None, List['JSON'], Dict[str, 'JSON']]


TPrimitiveHparams = Union[str, float, None, int, bool, Enum, "Hparams",]  # type: ignore
# We explicitely do not allow lists of mixed types
# For compatibility with third-party libraries we allow Dict[str, JSON]
THparams = Union[TPrimitiveHparams, List[str], List[float], List[int], List[Enum], List["Hparams"],  # type: ignore
                 Dict[str, "JSON",],]
