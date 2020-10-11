import json
from typing import Any

# Inspired by https://stackoverflow.com/a/26512016
class JSONEncoder(json.JSONEncoder):
    def __init__(self, *args: Any, **kwargs: Any):
        super(JSONEncoder, self).__init__(*args, **kwargs)
        self.indent_n = 0
    @property
    def indent_str(self) -> str:
        return ' ' * self.indent_n
    def encode(self, o: Any) -> str:
        if isinstance(o, list):
            primitives = not any([isinstance(i, (list, dict)) for i in o])
            if primitives:
                out = [str(i) for i in o]
                return '[' + ', '.join(out) + ']'
            self.indent_n += self.indent
            out = [self.indent_str + self.encode(i) for i in o]
            self.indent_n -= self.indent
            return '[\n' + ',\n'.join(out) + '\n' + self.indent_str + ']'
        if isinstance(o, dict):
            self.indent_n += self.indent
            out = [(self.indent_str + str(k) + ': '
                + self.encode(v)) for k, v in o.items()]
            self.indent_n -= self.indent
            return '{\n' + ',\n'.join(out) + '\n' + self.indent_str + '}'
        return json.dumps(o, default=str)

def dumps(obj: Any, indent: int = 2, cls: type = JSONEncoder, **kwargs: Any) -> str:
    return json.dumps(obj, indent=indent, cls=cls, **kwargs)
