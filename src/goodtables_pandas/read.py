import csv
from typing import Dict, List, Union

import goodtables
import pandas as pd

class CSVDialect(csv.Dialect):
    def __init__(self, dialect: dict = {}):
        self.delimiter = dialect.get('delimiter', ',')
        self.doublequote = dialect.get('doubleQuote', True)
        self.escapechar = dialect.get('escapeChar', None)
        self.lineterminator = dialect.get('lineTerminator', '\n')
        self.quotechar = dialect.get('quoteChar', '"')
        self.quoting = csv.QUOTE_MINIMAL
        self.skipinitialspace = dialect.get('skipInitialSpace', True)
        self.strict = True

def read_table(resource: dict, path: str = None) -> Union[pd.DataFrame, List[goodtables.Error]]:
    schema = resource.get('schema', {})
    dialect = resource.get('dialect', {})
    kwargs = dict(
        header=0 if dialect.get('header', True) else None,
        names=None if dialect.get('header', True) else [field['name'] for field in schema['fields']],
        index_col=False,
        squeeze=False,
        dtype=str,
        engine='c',
        na_values=schema.get('missingValues', ['']) + list(dialect.get('nullSequence', [])),
        keep_default_na=False,
        na_filter=True,
        skip_blank_lines=False,
        comment=dialect.get('commentChar', None),
        encoding=resource.get('encoding', 'utf-8'),
        dialect=CSVDialect(dialect),
        error_bad_lines=True,
        low_memory=True)
    path = path if path else resource.get('path')
    if isinstance(path, str):
        path = [path]
    tables = []
    for p in path:
        try:
            tables.append(pd.read_csv(p, **kwargs))
        except Exception as e:
            return [goodtables.Error(code='io-error', message=str(e))]
    return pd.concat(tables)
