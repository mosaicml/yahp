from typing import Any, Optional, TextIO

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
