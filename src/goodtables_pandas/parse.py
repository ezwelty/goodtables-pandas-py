"""Parse and validate table fields."""
import base64
import datetime
import re
from typing import Any, Iterable, List, Tuple, Union

import numpy as np
import pandas as pd
from typing_extensions import Literal

from . import options as OPTIONS
from .errors import ConstraintTypeError
from .errors import TypeError as ValueTypeError


def parse_table(
    df: pd.DataFrame, schema: dict
) -> Union[pd.DataFrame, List[ValueTypeError]]:
    """
    Parse table.

    Arguments:
        df: Table.
        schema: Table schema (https://specs.frictionlessdata.io/table-schema).

    Returns:
        Either a table of parsed fields and values, or a list of errors.
    """
    errors = []
    for field in schema.get("fields", []):
        result = parse_field(df[field["name"]], **field)
        if isinstance(result, ValueTypeError):
            # HACK: Add field name to parsing error
            result["fieldName"] = field["name"]
            result["message"] = result.template.format(**result)
            errors.append(result)
        else:
            df[field["name"]] = result
    return errors or df


def parse_field(
    x: pd.Series, type: str = "string", **field: Any
) -> Union[pd.Series, ValueTypeError]:
    """
    Parse table field.

    Arguments:
        x: Field values.
        type: Field type.
        field: Additional field attributes
            (https://specs.frictionlessdata.io/table-schema/#field-descriptors).

    Raises:
        NotImplementedError: Field type not supported.

    Returns:
        Either a series of parsed field values, or an error.
    """
    parser = globals().get(f"parse_{type}", None)
    if not parser:
        raise NotImplementedError(f"Field type not supported: {type}")
    argnames = parser.__code__.co_varnames[1 : parser.__code__.co_argcount]
    field = {key: field[key] for key in argnames if key in field}
    return parser(x, **field)


def parse_field_constraint(
    x: Union[str, int, float, bool, list],
    constraint: str,
    type: str = "string",
    **field: Any,
) -> Union[str, int, float, bool, list, datetime.datetime, ConstraintTypeError]:
    """
    Parse field constraint.

    Arguments:
        x: Constraint value.
        constraint: Constraint type.
        type: Field type.
        field: Additional field attributes
            (https://specs.frictionlessdata.io/table-schema/#field-descriptors).

    Returns:
        Parsed field constraint.
    """
    is_list = isinstance(x, list)
    X = pd.Series(x)
    is_str = X.apply(lambda xi: isinstance(xi, str))
    if not is_str.any():
        return x
    result = parse_field(X[is_str], type=type, **field)
    if isinstance(result, ValueTypeError):
        return ConstraintTypeError(
            fieldName=field.get("name", ""),
            constraintName=constraint,
            constraintValue=X[is_str].unique().tolist() if is_list else x,
            fieldType=type,
            fieldFormat=result["fieldFormat"],
        )
    X[is_str] = result
    return X.tolist() if is_list else X[0]


# ---- Field parsers ----


def _validate_string_binary(xi: str) -> bool:
    try:
        base64.b64decode(xi)
        return True
    except Exception:
        return False


def parse_string(
    x: pd.Series,
    format: Literal["default", "email", "uri", "binary", "uuid"] = "default",
) -> Union[pd.Series, ValueTypeError]:
    """
    Parse field values as string.

    Email (https://en.wikipedia.org/wiki/Email_address#Syntax):
    The local part is limited to 64 characters. It may contain characters `a-z`, `A-Z`,
    `0-9`, `!#$%&'*+-/=?^_`{|}~`, and `.` if it is not first, last, or appearing
    consecutively (`..`). The DNS labels in the domain name are limited to 63 characters
    each. They may contain characters `a-z`, `A-Z`, `0-9`, and `-` if it is not first or
    last. Comments, IP address literals, quoted local parts, and internationalized
    domain names are not currently supported.

    Uniform Resource Identifier
    (https://en.wikipedia.org/wiki/Uniform_Resource_Identifier):
    The scheme must start with a letter (`a-zA-Z`) and may contain characters `a-z`,
    `A-Z`, `0-9`, and `+.-`. It must be followed by `:`, optionally `//`, and one or
    more non-whitespace characters. No additional validation is performed.

    Base64 string-encoded binary (https://en.wikipedia.org/wiki/Base64):
    Blocks of four characters (`a-z`, `A-Z`, `0-9`, and `+/`)
    padded with `=` to ensure the last block contains four characters.
    Whitespace is ignored, per RFC 4648 (https://www.ietf.org/rfc/rfc4648.txt).

    Universally unique identifier
    (https://en.wikipedia.org/wiki/Universally_unique_identifier#Format):
    Blocks of characters `a-f`, `A-F`, and `0-9` of length, 8, 4, 4, 4, 12,
    separated by `-`.

    Arguments:
        x: Field values.
        format: String format.

    Returns:
        Either the parsed field values or an error.
    """
    patterns = {
        "email": (
            r"^(?=[^@]{1,64}@)[a-z0-9!#$%&'\*\+\-\/=\?\^_`{|}~]+"
            r"(?:\.[a-z0-9!#$%&'\*\+\-\/=\?\^_`{|}~]+)*@(?=[^.]{1,63}"
            r"(?:\.|$))[a-z0-9]+(?:\-[a-z0-9]+)*(?:\.(?=[^.]{1,63}"
            r"(?:\.|$))[a-z0-9]+(?:\-[a-z0-9]+)*)+$"
        ),
        "uri": r"^[a-z][a-z0-9+.-]*:(?:\/\/[^\s]+|[^\s\/][^\s]*)$",
        "uuid": r"^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$",
    }
    if format != "default":
        mask = ~x.isna()
        if format == "binary":
            invalid = ~x[mask].apply(_validate_string_binary)
        else:
            pattern = patterns[format]
            invalid = ~x[mask].str.contains(pattern, flags=re.IGNORECASE)
        if invalid.any():
            return ValueTypeError(
                fieldType="string",
                fieldFormat=format,
                values=x[mask][invalid].dropna().unique().tolist(),
            )
    return x


_NUMBER_PATTERN = re.compile(
    r"([+-]?(?:nan|inf(?:inity)?|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:e[+-]?[0-9]+)?))",
    flags=re.IGNORECASE,
)


def _extract_number(xi: Union[str, float]) -> str:
    try:
        parts = _NUMBER_PATTERN.findall(xi)
        if len(parts) == 1:
            return _parse_number(parts[0])
        return "NULL"
    except TypeError:
        return "NULL"


def _parse_number(xi: Union[str, float]) -> Union[float, str]:
    try:
        return float(xi)
    except ValueError:
        return "NULL"


def parse_number(
    x: pd.Series, decimalChar: str = ".", groupChar: str = None, bareNumber: bool = True
) -> Union[pd.Series, ValueTypeError]:
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
    parsed = x
    if groupChar:
        parsed = parsed.str.replace(groupChar, "", regex=False)
    if decimalChar != ".":
        parsed = parsed.str.replace(decimalChar, ".", regex=False)
    if OPTIONS.raise_first_invalid_number:
        try:
            return parsed.astype(float)
        except ValueError as e:
            return ValueTypeError(fieldType="number", note=str(e))
    if bareNumber:
        parsed = parsed.apply(_parse_number, convert_dtype=False)
    else:
        parsed = parsed.apply(_extract_number, convert_dtype=False)
    # HACK: Use 'NULL' to distinguish values parsed as NaN from parsing failures
    # Use isin (not ==) to avoid warning that elementwise comparison failed
    unparsed = parsed.isin(["NULL"])
    invalid = ~x.isna() & unparsed
    if invalid.any():
        invalids = x[invalid].unique().tolist()
        return ValueTypeError(fieldType="number", values=invalids)
    # Replace 'NULL' with NaN
    return parsed.where(~unparsed).astype(float)


_INTEGER_PATTERN = re.compile(r"([+-]?[0-9]+)")


def _extract_integer(xi: Union[str, float]) -> Union[str, float]:
    try:
        parts = _INTEGER_PATTERN.findall(xi)
        if len(parts) == 1:
            return _parse_integer(parts[0])
        return np.nan
    except TypeError:
        return np.nan


def _parse_integer(xi: Union[str, float]) -> Union[int, float]:
    try:
        return int(xi)
    except ValueError:
        return np.nan


def parse_integer(
    x: pd.Series, bareNumber: bool = True
) -> Union[pd.Series, ValueTypeError]:
    """
    Parse strings as integers.

    Arguments:
        x: Strings.
        bareNumber: Whether the numbers are bare, or padded with non-numeric text.

    Returns:
        Either parsed integers or a parsing error.
    """
    if OPTIONS.raise_first_invalid_integer:
        isna = x.isna()
        try:
            x = x.where(isna, x[~isna].astype(int))
            return x.astype("Int64")
        except ValueError as e:
            return ValueTypeError(fieldType="integer", note=str(e))
    parsed = x
    if bareNumber:
        parsed = parsed.apply(_parse_integer, convert_dtype=False)
    else:
        parsed = parsed.apply(_extract_integer, convert_dtype=False)
    invalid = ~x.isna() & parsed.isna()
    if invalid.any():
        invalids = x[invalid].unique().tolist()
        return ValueTypeError(fieldType="integer", values=invalids)
    return parsed.astype("Int64")


def parse_boolean(
    x: pd.Series,
    trueValues: Iterable[str] = ("true", "True", "TRUE", "1"),
    falseValues: Iterable[str] = ("false", "False", "FALSE", "0"),
) -> Union[pd.Series, ValueTypeError]:
    """
    Parse strings as boolean.

    Arguments:
        x: Strings.
        trueValues: Strings representing `False`.
        falseValues: Strings representing `True`.

    Returns:
        Either parsed boolean (as :class:`pd.Int64Dtype`) or a parsing error.
    """
    true = x.isin(trueValues)
    false = x.isin(falseValues)
    na = x.isna()
    invalid = ~(true | false | na)
    if invalid.any():
        invalids = x[invalid].unique().tolist()
        return ValueTypeError(fieldType="boolean", values=invalids)
    x = true.astype(int).astype("Int64")
    x[na] = np.nan
    return x


def parse_date(
    x: pd.Series, format: str = "default"
) -> Union[pd.Series, ValueTypeError]:
    """
    Parse strings as dates.

    Because :class:`pd.Timestamp` is used, dates are limited to the range 1677 - 2262
    (https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timestamp-limitations).

    Arguments:
        x: Strings.
        format: Either 'default' (ISO8601: `YYY-MM-DD`), 'any' (guess),
            or a pattern compatible with :meth:`datetime.datetime.strptime`.

    Returns:
        Either parsed dates (as :class:`pd.Timestamp`) or a parsing error.
    """
    patterns = {"default": "%Y-%m-%d", "any": None}
    pattern = patterns.get(format, format)
    parsed = pd.to_datetime(
        x, errors="coerce", format=pattern, infer_datetime_format=pattern is None
    )
    invalid = ~x.isna() & parsed.isna()
    if invalid.any():
        invalids = x[invalid].unique().tolist()
        return ValueTypeError(fieldType="date", fieldFormat=format, values=invalids)
    return parsed


def parse_datetime(
    x: pd.Series, format: str = "default"
) -> Union[pd.Series, ValueTypeError]:
    """
    Parse strings as datetimes.

    Because :class:`pd.Timestamp` is used, dates are limited to the range 1677 - 2262
    (https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timestamp-limitations).

    Arguments:
        x: Strings.
        format: Either 'default' (ISO8601: `YYY-MM-DDThh:mm:ssZ`), 'any' (guess),
            or a pattern compatible with :meth:`datetime.datetime.strptime`.

    Returns:
        Either parsed datetimes (as :class:`pd.Timestamp`) or a parsing error.
    """
    patterns = {"default": "%Y-%m-%dT%H:%M:%S%z", "any": None}
    pattern = patterns.get(format, format)
    parsed = pd.to_datetime(
        x, errors="coerce", format=pattern, infer_datetime_format=pattern is None
    )
    invalid = ~x.isna() & parsed.isna()
    if invalid.any():
        invalids = x[invalid].unique().tolist()
        return ValueTypeError(fieldType="datetime", fieldFormat=format, values=invalids)
    return parsed


def parse_year(x: pd.Series) -> Union[pd.Series, ValueTypeError]:
    """
    Parse strings as years.

    Per XML Schema, permits negative years and years greater than 9999.
    However, time zones are not supported
    (https://www.w3.org/TR/xmlschema-2/#timeZonePermited).

    Arguments:
        x: Strings.

    Returns:
        Either parsed years (as :class:`pd.Int64Dtype`) or a parsing error.
    """
    parsed = x.apply(_extract_integer, convert_dtype=False)
    invalid = ~x.isna() & parsed.isna()
    if invalid.any():
        invalids = x[invalid].unique().tolist()
        return ValueTypeError(fieldType="year", values=invalids)
    return parsed.astype("Int64")


_GEOPOINT_PATTERN_DEFAULT = re.compile(r"^([^, ]+), ?([^ ]+)$")


def _extract_geopoint_default(xi: str) -> Union[Tuple[float, float], float]:
    parts = _GEOPOINT_PATTERN_DEFAULT.findall(xi)
    try:
        return float(parts[0][0]), float(parts[0][1])
    except (ValueError, IndexError):
        return np.nan


_GEOPOINT_PATTERN_ARRAY = re.compile(r"^\s*\[\s*(.+),\s*(.+)\s*\]\s*$")


def _extract_geopoint_array(xi: str) -> Union[Tuple[float, float], float]:
    parts = _GEOPOINT_PATTERN_ARRAY.findall(xi)
    try:
        return float(parts[0][0]), float(parts[0][1])
    except (ValueError, IndexError):
        return np.nan


_GEOPOINT_PATTERN_LONLAT = re.compile(
    r'^\s*\{\s*"lon":\s*(.+),\s*"lat":\s*(.+)\s*\}\s*$'
)
_GEOPOINT_PATTERN_LATLON = re.compile(
    r'^\s*\{\s*"lat":\s*(.+),\s*"lon":\s*(.+)\s*\}\s*$'
)


def _extract_geopoint_object(xi: str) -> Union[Tuple[float, float], float]:
    parts = _GEOPOINT_PATTERN_LONLAT.findall(xi)
    if not parts:
        parts = _GEOPOINT_PATTERN_LATLON.findall(xi)
        if parts:
            parts[0] = parts[0][1], parts[0][0]
    try:
        return float(parts[0][0]), float(parts[0][1])
    except (IndexError, ValueError):
        return np.nan


def parse_geopoint(
    x: pd.Series, format: Literal["default", "array", "object"] = "default"
) -> Union[pd.Series, ValueTypeError]:
    """
    Parse strings as geopoints.

    Per XML Schema, permits negative years and years greater than 9999.
    However, time zones are not supported
    (https://www.w3.org/TR/xmlschema-2/#timeZonePermited).

    Arguments:
        x: Strings.
        format: Either 'default' ('<lon>,<lat>' or '<lon>, <lat>'),
            'array' ('[<lon>, <lat>]', whitespace-insensitive), or
            'object' ('{"lon": <lon>, "lat": <lat>}' or '{"lat": <lat>, "lon": <lon>}',
            whitespace-insensitive),
            where `<lon>` and `<lat>` are any values accepted by :class:`float`.

    Returns:
        Either parsed geopoints (as :class:`tuple`: lon, lat) or a parsing error.
    """
    mask = ~x.isna()
    functions = {
        "default": _extract_geopoint_default,
        "array": _extract_geopoint_array,
        "object": _extract_geopoint_object,
    }
    parsed = x[mask].apply(functions[format])
    invalid = parsed.isna()
    if invalid.any():
        invalids = x[mask][invalid].unique().tolist()
        return ValueTypeError(fieldType="geopoint", fieldFormat=format, values=invalids)
    return parsed.reindex_like(x)
