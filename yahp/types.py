# Copyright 2021 MosaicML. All Rights Reserved.
"""Type Annotations used by YAHP

Attributes:
    JSON: Representation for JSON-like types.
    HparamsField: Union of allowed types for :class:`~yahp.hparams.Hparams` fields.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Union

import yahp as hp

JSON = Union[str, float, int, None, List['JSON'], Dict[str, 'JSON']]

HparamsField = Union[str, float, Enum, hp.Hparams, int, None, List[hp.Hparams], List[str], List[float], List[int],
                     List[Enum], Dict[str, JSON], List[Union[str, float]], List[Union[str, int]],]
