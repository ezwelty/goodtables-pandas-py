"""Read tabular data from csv files."""
import csv
from typing import Iterable, List, Union

import frictionless
import pandas as pd


class CSVDialect(csv.Dialect):
    """
    Dialect for parsing CSV files instantiated from a CSV Dialect descriptor.

    Arguments:
        dialect: CSV Dialect (https://specs.frictionlessdata.io/csv-dialect).
    """

    def __init__(self, dialect: dict = {}) -> None:  # noqa: ANN101
        self.delimiter = dialect.get("delimiter", ",")
        self.doublequote = dialect.get("doubleQuote", True)
        self.escapechar = dialect.get("escapeChar", None)
        self.lineterminator = dialect.get("lineTerminator", "\n")
        self.quotechar = dialect.get("quoteChar", '"')
        self.quoting = csv.QUOTE_MINIMAL
        self.skipinitialspace = dialect.get("skipInitialSpace", True)
        self.strict = True


def read_table(
    resource: dict, path: Union[str, Iterable[str]] = None
) -> Union[pd.DataFrame, List[frictionless.errors.SourceError]]:
    """
    Read table from path(s).

    Arguments:
        resource: Tabular Data Resource descriptor
            (https://specs.frictionlessdata.io/tabular-data-resource).
        path: Path(s) to files to read. If `None`, `resource['path']` is used.

    Returns:
        Table.
    """
    schema = resource.get("schema", {})
    dialect = resource.get("dialect", {})
    kwargs = dict(
        header=0 if dialect.get("header", True) else None,
        names=None
        if dialect.get("header", True)
        else [field["name"] for field in schema["fields"]],
        index_col=False,
        squeeze=False,
        dtype=str,
        engine="c",
        na_values=schema.get("missingValues", [""])
        + list(dialect.get("nullSequence", [])),
        keep_default_na=False,
        na_filter=True,
        skip_blank_lines=False,
        comment=dialect.get("commentChar", None),
        encoding=resource.get("encoding", "utf-8"),
        dialect=CSVDialect(dialect),
        error_bad_lines=True,
        low_memory=True,
    )
    path = path if path else resource.get("path")
    if isinstance(path, str):
        path = [path]
    tables = []
    for p in path:
        try:
            tables.append(pd.read_csv(p, **kwargs))
        except Exception as e:
            return [frictionless.errors.SourceError(note=str(e))]
    return pd.concat(tables)
