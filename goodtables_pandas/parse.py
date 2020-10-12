import datetime
import re
from typing import Any, Iterable, List, Literal, Union

import goodtables
import numpy as np
import pandas as pd

from .errors import type_or_format_error, constraint_type_or_format_error

def parse_table(df: pd.DataFrame, schema: dict) -> Union[pd.DataFrame, List[goodtables.Error]]:
    errors = []
    for field in schema.get('fields', []):
        result = parse_field(df[field['name']], **field)
        if isinstance(result, goodtables.Error):
            result._message_substitutions['name'] = field['name']
            errors.append(result)
        else:
            df[field['name']] = result
    return errors or df

def parse_field(x: pd.Series, type: str = 'string', **field: Any) -> Union[pd.Series, goodtables.Error]:
    parser = globals().get(f'parse_{type}', None)
    if not parser:
        raise NotImplementedError(f'Field type not supported: {type}')
    argnames = parser.__code__.co_varnames[1:parser.__code__.co_argcount]
    field = {key: field[key] for key in argnames if key in field}
    return parser(x, **field)

def parse_field_constraint(x: Union[str, int, float, bool, list], constraint: str, type: str = 'string', **field: Any) -> Union[str, int, float, bool, list, datetime.datetime, goodtables.Error]:
    is_list = isinstance(x, list)
    X = pd.Series(x)
    is_str = X.apply(lambda xi: isinstance(xi, str))
    if not is_str.any():
        return x
    result = parse_field(X[is_str], type=type, **field)
    if isinstance(result, goodtables.Error):
        data = result._message_substitutions
        return constraint_type_or_format_error(
            name=field.get('name', 'field'), constraint=constraint,
            value=X[is_str].unique().tolist() if is_list else x,
            type=type, format=data['format'])
    X[is_str] = result
    return X.tolist() if is_list else X[0]

# ---- Field parsers ----

def parse_string(x: pd.Series, format: Literal['default', 'email', 'uri', 'binary', 'uuid'] = 'default') -> Union[pd.Series, goodtables.Error]:
    """
    Parse field values as string.

    Email (https://en.wikipedia.org/wiki/Email_address#Syntax):
    The local part is limited to 64 characters. It may contain characters `a-z`, `A-Z`,
    `0-9`, `!#$%&'*+-/=?^_`{|}~`, and `.` if it is not first, last, or appearing
    consecutively (`..`). The DNS labels in the domain name are limited to 63 characters
    each. They may contain characters `a-z`, `A-Z`, `0-9`, and `-` if it is not first or
    last. Comments, IP address literals, quoted local parts, and internationalized
    domain names are not currently supported.

    Uniform Resource Identifier (https://en.wikipedia.org/wiki/Uniform_Resource_Identifier):
    The scheme must start with a letter (`a-zA-Z`) and may contain characters `a-z`,
    `A-Z`, `0-9`, and `+.-`. It must be followed by `:`, optionally `//`, and one or
    more non-whitespace characters. No additional validation is performed.

    Base64 string-encoded binary (https://en.wikipedia.org/wiki/Base64):
    Blocks of four characters (`a-z`, `A-Z`, `0-9`, and `+/`)
    padded with `=` to ensure the last block contains four characters.
    Whitespace is ignored, per RFC 4648 (https://www.ietf.org/rfc/rfc4648.txt).

    Universally unique identifier (https://en.wikipedia.org/wiki/Universally_unique_identifier#Format):
    Blocks of characters `a-f`, `A-F`, and `0-9` of length, 8, 4, 4, 4, 12, separated by `-`.

    Arguments:
        x: Field values.
        format: String format.

    Returns:
        Either the parsed field values or an error.
    """
    patterns = {
        'email': r"^(?=[^@]{1,64}@)[a-z0-9!#$%&'\*\+\-\/=\?\^_`{|}~]+(?:\.[a-z0-9!#$%&'\*\+\-\/=\?\^_`{|}~]+)*@(?=[^.]{1,63}(?:\.|$))[a-z0-9]+(?:\-[a-z0-9]+)*(?:\.(?=[^.]{1,63}(?:\.|$))[a-z0-9]+(?:\-[a-z0-9]+)*)+$",
        'uri': r"^[a-z][a-z0-9+.-]*:(?:\/\/[^\s]+|[^\s\/][^\s]*)$",
        'binary': r"^(?:[a-z0-9+\/]{4})*(?:[a-z0-9+\/]{2}==|[a-z0-9+\/]{3}=)?$",
        'uuid': r"^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$"
    }
    pattern = patterns.get(format)
    if pattern:
        if format == 'binary':
            invalid = ~x.str.replace(r'\s', '').str.contains(pattern, flags=re.IGNORECASE)
        else:
            invalid = ~x.str.contains(pattern, flags=re.IGNORECASE)
        if invalid.any():
            return type_or_format_error(
                type='string', format=format,
                values=x[invalid].dropna().unique().tolist())
    return x

def _parse_number(xi: str) -> Union[float, str]:
    try:
        return float(xi)
    except ValueError:
        return 'NULL'

def parse_number(x: pd.Series, decimalChar: str = '.', groupChar: str = None, bareNumber: bool = True) -> Union[pd.Series, goodtables.Error]:
    """
    Parse strings as numbers.

    Unlike Table Schema, the special string values `-nan`, `infinity`, and `-infinity`
    are also permitted.

    Arguments:
        x: Strings.
        decimalChar: String used to represent a decimal point. Can be of any length.
        groupChar: String used to group digits. Can be of any length.
        bareNumber: Whether the numbers are bare, or padded with non-numeric text.

    Returns:
        Either parsed numbers or a parsing error.
    """
    if groupChar:
        x = x.str.replace(groupChar, '', regex=False)
    if decimalChar != '.':
        x = x.str.replace(decimalChar, '.', regex=False)
    if not bareNumber:
        pattern = r"([+-]?(?:nan|inf(?:inity)?|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:e[+-]?[0-9]+)?))"
        x = x.str.extract(pattern, expand=False, flags=re.IGNORECASE)
    parsed = x.apply(_parse_number)
    # HACK: Use 'NULL' to distinguish values parsed as NaN from parsing failures
    # Use isin (not ==) to avoid warning that elementwise comparison failed
    unparsed = parsed.isin(['NULL'])
    invalid = ~x.isna() & unparsed
    if invalid.any():
        invalids = x[invalid].unique().tolist()
        return type_or_format_error(type='number', values=invalids)
    # Replace 'NULL' with NaN
    return parsed.where(~unparsed).astype(float)

def parse_integer(x: pd.Series, bareNumber: bool = True) -> Union[pd.Series, goodtables.Error]:
    oid = id(x)
    if not bareNumber:
        number = r"(-?[0-9]+)"
        x = x.str.lower().str.extract(number, expand=False)
    na = x.isna()
    if id(x) == oid:
        x = x.copy()
    try:
        x[~na] = x[~na].astype(int)
        return x.astype('Int64')
    except ValueError as e:
        return type_or_format_error(message=str(e), type='integer')

def parse_boolean(
    x: pd.Series, trueValues: Iterable[str] = ('true', 'True', 'TRUE', '1'),
    falseValues: Iterable[str] = ('false', 'False', 'FALSE', '0')) -> Union[pd.Series, goodtables.Error]:
    true = x.isin(trueValues)
    false = x.isin(falseValues)
    na = x.isna()
    invalid = ~(true | false | na)
    if invalid.any():
        invalids = x[invalid].unique().tolist()
        return type_or_format_error(type='boolean', values=invalids)
    x = true.astype(int).astype('Int64')
    x[na] = np.nan
    return x

def parse_date(x: pd.Series, format: str = 'default') -> Union[pd.Series, goodtables.Error]:
    patterns = {'default': '%Y-%m-%d', 'any': None}
    pattern = patterns.get(format, format)
    parsed = pd.to_datetime(x, errors='coerce', format=pattern, infer_datetime_format=True)
    invalid = ~x.isna() & parsed.isna()
    if invalid.any():
        invalids = x[invalid].unique().tolist()
        return type_or_format_error(type='date', format=format, values=invalids)
    return parsed

def parse_datetime(x: pd.Series, format: str = 'default') -> Union[pd.Series, goodtables.Error]:
    patterns = {'default': '%Y-%m-%dT%H:%M:%SZ', 'any': None}
    pattern = patterns.get(format, format)
    parsed = pd.to_datetime(x, errors='coerce', format=pattern, infer_datetime_format=True)
    invalid = ~x.isna() & parsed.isna()
    if invalid.any():
        invalids = x[invalid].unique().tolist()
        return type_or_format_error(type='datetime', format=format, values=invalids)
    return parsed

def parse_year(x: pd.Series) -> Union[pd.Series, goodtables.Error]:
    na = x.isna()
    x = x.copy()
    try:
        # NOTE: Does not permit timezone specification
        # https://www.w3.org/TR/xmlschema-2/#timeZonePermited
        x[~na] = x[~na].astype(int)
        return x.astype('Int64')
    except ValueError as e:
        return type_or_format_error(message=str(e), type='year')

def parse_geopoint(x: pd.Series, format: Literal['default', 'array', 'object'] = 'default') -> Union[pd.Series, goodtables.Error]:
    mask = ~x.isna()
    if format in ('default', 'array'):
        pattern = r'^(?P<lon>.*), *(?P<lat>.*)$' if format == 'default' else r'^\[ *(?P<lon>.*), *(?P<lat>.*) *\]$'
        parsed = x[mask].str.extract(pattern, expand=True).apply(pd.to_numeric, axis=1, errors='coerce')
    elif format == 'object':
        # apply(json.loads) much slower than str.extract(pattern)
        pattern = r'^\{ *"lon": *(?P<lon>.*), *"lat": *(?P<lat>.*) *\}$'
        parsed = x[mask].str.extract(pattern, expand=True).apply(pd.to_numeric, axis=1, errors='coerce')
        missing = parsed.isna().any(axis=1)
        pattern = r'^\{ *"lat": *(?P<lat>.*), *"lon": *(?P<lon>.*) *\}$'
        parsed[missing] = x[mask][missing].str.extract(pattern).apply(pd.to_numeric, axis=1, errors='coerce')
    invalid = parsed.isna().any(axis=1)
    if invalid.any():
        invalids = x[mask][invalid].unique().tolist()
        return type_or_format_error(type='geopoint', format=format, values=invalids)
    return pd.Series(zip(parsed['lon'], parsed['lat']), index=parsed.index).reindex_like(x)
