"""Custom JSON encoding."""
import json
from typing import Any


# Inspired by https://stackoverflow.com/a/26512016
class _JSONEncoder(json.JSONEncoder):
    """A JSON Encoder that prints each list on a single line."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN101
        super(_JSONEncoder, self).__init__(*args, **kwargs)
        self.indent_n = 0

    @property
    def indent_str(self) -> str:  # noqa: ANN101
        return " " * self.indent_n

    def encode(self, o: Any) -> str:  # noqa: ANN101
        if isinstance(o, list):
            primitives = not any([isinstance(i, (list, dict)) for i in o])
            if primitives:
                out = [str(i) for i in o]
                return "[" + ", ".join(out) + "]"
            self.indent_n += self.indent
            out = [self.indent_str + self.encode(i) for i in o]
            self.indent_n -= self.indent
            return "[\n" + ",\n".join(out) + "\n" + self.indent_str + "]"
        if isinstance(o, dict):
            self.indent_n += self.indent
            out = [
                (self.indent_str + str(k) + ": " + self.encode(v)) for k, v in o.items()
            ]
            self.indent_n -= self.indent
            return "{\n" + ",\n".join(out) + "\n" + self.indent_str + "}"
        return json.dumps(o, default=str)


def dumps(obj: Any, **kwargs: Any) -> str:
    r"""
    Serialize an object to a JSON-like string.

    Overrides the default :class:`json.JSONEncoder` to maximize legibility when printed:

    - Places each list on a single line (when `indent` is used).
    - Does not wrap object keys in quotes ("), resulting in invalid JSON.

    Arguments:
        obj: Object to serialize.
        kwargs: Additional keyword arguments to :class:`json.JSONEncoder`.

    Returns:
        JSON-like string.

    Examples:
        >>> import json
        >>> obj = [0, 1]
        >>> json.dumps(obj, indent=2)
        '[\n  0,\n  1\n]'
        >>> dumps(obj, indent=2)
        '[0, 1]'
        >>> obj = {'x': 0, 'y': 1}
        >>> json.dumps(obj, indent=2)
        '{\n  "x": 0,\n  "y": 1\n}'
        >>> dumps(obj, indent=2)
        '{\n  x: 0,\n  y: 1\n}'
    """
    return json.dumps(obj, cls=_JSONEncoder, **kwargs)
