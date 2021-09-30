from dataclasses import asdict, dataclass
from typing import Any, Optional, Sequence, TextIO, Type

import yaml

# This is for ruamel.yaml not importing properly in conda
try:
    from ruamel_yaml import YAML  # type: ignore
    from ruamel_yaml.compat import StringIO  # type: ignore
except ImportError as e:
    from ruamel.yaml import YAML  # type: ignore
    from ruamel.yaml.compat import StringIO  # type: ignore


class YAHPException(Exception):
    pass


class StringDumpYAML(YAML):  # type: ignore

    def dump(self, data: Any, stream: Optional[TextIO] = None, **kw: Any):
        stream_found = True
        if stream is None:
            # Check if steam exists, otherwise create StringIO in memory stream
            stream_found = False
            stream = StringIO()
        YAML.dump(self, data, stream, **kw)
        if not stream_found:
            return stream.getvalue()  # type: ignore


@dataclass
class ParserArgument:

    arg_type: Type[Any]
    full_arg_name: str
    required: bool
    helptext: str
    default: Optional[Any]
    const: Optional[Any] = None
    nargs: Optional[str] = None
    choices: Sequence[str] = ()
    short_arg_name: Optional[str] = None
    is_hparams_subclass: bool = False

    def get_possible_short_name(self, index: int = 0):
        items = self.get_namespace_name().split(".")[-(index + 1):]
        return ".".join(items)

    def get_namespace_name(self):
        return self.full_arg_name.replace("--", "")

    def __str__(self) -> str:
        return yaml.dump(asdict(self))
