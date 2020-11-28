"""Table keys and field constraint checking."""
from typing import Any, Dict, Iterable, List, Union

import pandas as pd
from typing_extensions import Literal

from .errors import (
    ConstraintError,
    ConstraintTypeError,
    ForeignKeyError,
    PrimaryKeyError,
    UniqueKeyError,
)
from .parse import parse_field_constraint

# ---- Field constraints ----


def check_constraints(
    df: pd.DataFrame, schema: dict
) -> List[Union[ConstraintError, ConstraintTypeError]]:
    """
    Check table field constraints.

    Arguments:
        df: Table.
        schema: Table schema (https://specs.frictionlessdata.io/table-schema).

    Returns:
        A list of errors.
    """
    errors = []
    for field in schema.get("fields", []):
        constraints = field.get("constraints", {})
        result = check_field_constraints(df[field["name"]], **constraints, field=field)
        if result:
            errors += result
    return errors


def check_field_constraints(  # noqa: C901
    x: pd.Series,
    required: bool = False,
    unique: bool = False,
    minLength: int = None,
    maxLength: int = None,
    minimum: Union[str, int, float, bool] = None,
    maximum: Union[str, int, float, bool] = None,
    pattern: str = None,
    enum: Iterable[Union[str, int, float, bool]] = None,
    field: dict = {},
) -> List[Union[ConstraintError, ConstraintTypeError]]:
    """
    Check field constraints.

    See https://specs.frictionlessdata.io/table-schema/#constraints.

    Arguments:
        x: Field values.
        required: Whether values must not be null.
        unique: Whether values must be unique.
        minLength: Minimum length.
        maxLength: Maximum length.
        minimum: Minimum value.
        maximum: Maximum value.
        pattern: Regular expression.
        enum: Values which field values must match exactly.
        field: Field descriptor
            (https://specs.frictionlessdata.io/table-schema/#field-descriptors).

    Returns:
        A list of errors.
    """
    name = field.get("name", "field")
    type = field.get("type", "string")
    errors = []
    if required and x.isna().any():
        errors.append(
            ConstraintError(
                fieldName=name,
                constraintName="required",
                constraintValue=required,
                values=[float("nan")],
            )
        )
    if unique:
        # NOTE: Pandas considers nulls equal (not unique)
        invalid = x.duplicated()
        if invalid.any():
            errors.append(
                ConstraintError(
                    fieldName=name,
                    constraintName="unique",
                    constraintValue=unique,
                    values=list(x[invalid].unique()),
                )
            )
    x = x.dropna()
    length_types = ("string", "array", "object")
    if minLength is not None and type in length_types:
        invalid = x.str.len() < minLength
        if invalid.any():
            errors.append(
                ConstraintError(
                    fieldName=name,
                    constraintName="minLength",
                    constraintValue=minLength,
                    values=list(x[invalid].unique()),
                )
            )
    if maxLength is not None and type in length_types:
        invalid = x.str.len() > maxLength
        if invalid.any():
            errors.append(
                ConstraintError(
                    fieldName=name,
                    constraintName="minLength",
                    constraintValue=maxLength,
                    values=list(x[invalid].unique()),
                )
            )
    minmax_types = (
        "integer",
        "number",
        "date",
        "time",
        "datetime",
        "year",
        "yearmonth",
    )
    if minimum is not None and type in minmax_types:
        minimum = parse_field_constraint(minimum, "minimum", **field)
        if isinstance(minimum, ConstraintTypeError):
            errors.append(minimum)
        else:
            invalid = x < minimum
            if invalid.any():
                errors.append(
                    ConstraintError(
                        fieldName=name,
                        constraintName="minimum",
                        constraintValue=minimum,
                        values=list(x[invalid].unique()),
                    )
                )
    if maximum is not None and type in minmax_types:
        maximum = parse_field_constraint(maximum, "maximum", **field)
        if isinstance(maximum, ConstraintTypeError):
            errors.append(maximum)
        else:
            invalid = x > maximum
            if invalid.any():
                errors.append(
                    ConstraintError(
                        fieldName=name,
                        constraintName="maximum",
                        constraintValue=maximum,
                        values=list(x[invalid].unique()),
                    )
                )
    if pattern and type in ("string",):
        invalid = ~x.str.match("^" + pattern + "$")
        if invalid.any():
            errors.append(
                ConstraintError(
                    fieldName=name,
                    constraintName="pattern",
                    constraintValue=pattern,
                    values=list(x[invalid].unique()),
                )
            )
    if enum:
        enum = parse_field_constraint(enum, "enum", **field)
        if isinstance(enum, ConstraintTypeError):
            errors.append(enum)
        else:
            invalid = ~x.isin(enum)
            if invalid.any():
                errors.append(
                    ConstraintError(
                        fieldName=name,
                        constraintName="enum",
                        constraintValue=enum,
                        values=list(x[invalid].unique()),
                    )
                )
    return errors


# ---- Key constraints ----


def _as_list(x: Any) -> List[Any]:
    """
    Convert non-list object to a list containing the object.

    Arguments:
        x: Object.

    Returns:
        The object, or a list containing the object.

    Examples:
        >>> _as_list(['ab'])
        ['ab']
        >>> _as_list('ab')
        ['ab']
    """
    if not isinstance(x, list):
        x = [x]
    return x


def check_primary_key(
    df: pd.DataFrame,
    primaryKey: Union[str, List[str]],
    skip_required: bool = False,
    skip_single: bool = False,
) -> List[Union[ConstraintError, PrimaryKeyError]]:
    """
    Check table primary key.

    Arguments:
        df: Table.
        primaryKey: Primary key field names.
        skip_required: Whether to not check for missing values in primary key fields.
        skip_single: Whether to not check for duplicates if primary key is one field.

    Returns:
        A list of errors.
    """
    errors = []
    key = _as_list(primaryKey)
    if key:
        if not skip_required:
            for name in key:
                errors += check_field_constraints(
                    df[name], required=True, field=dict(name=name)
                )
        if skip_single and len(key) < 2:
            return errors
        invalid = df.duplicated(subset=key)
        if invalid.any():
            errors.append(
                PrimaryKeyError(
                    primaryKey=key,
                    values=df[key][invalid].drop_duplicates().values.tolist(),
                )
            )
    return errors


def check_unique_keys(
    df: pd.DataFrame,
    uniqueKeys: Iterable[Union[str, List[str]]],
    skip_single: bool = False,
) -> List[Union[ConstraintError, UniqueKeyError]]:
    """
    Check table unique keys.

    Arguments:
        df: Table.
        uniqueKeys: Unique key field names.
        skip_single: Whether to not check for duplicates if unique key is one field.

    Returns:
        A list of errors.
    """
    errors = []
    for uniqueKey in uniqueKeys:
        key = _as_list(uniqueKey)
        if skip_single and len(key) < 2:
            continue
        invalid = df.duplicated(subset=key)
        if invalid.any():
            errors.append(
                UniqueKeyError(
                    uniqueKey=key,
                    values=df[key][invalid].drop_duplicates().values.tolist(),
                )
            )
    return errors


def check_foreign_keys(  # noqa: C901
    df: pd.DataFrame,
    foreignKeys: Iterable[dict],
    references: Dict[str, pd.DataFrame] = {},
    constraint: Literal["uniquekey", "primarykey"] = None,
) -> List[Union[ConstraintError, PrimaryKeyError, UniqueKeyError, ForeignKeyError]]:
    """
    Check table foreign keys.

    Arguments:
        df: Table.
        foreignKeys: Forein key descriptors
            (https://specs.frictionlessdata.io/table-schema/#foreign-keys).
        references: Foreign tables to check against.
        constraint: Whether to treat the key in the foreign table as a
            primary ('primarykey') or unique ('uniquekey') key.

    Returns:
        A list of errors.
    """
    errors = []
    child = df
    for foreignKey in foreignKeys:
        parent_name = foreignKey["reference"]["resource"]
        if parent_name == "":
            parent = child
        else:
            if parent_name in references:
                parent = references[parent_name]
            else:
                continue
        ckey = _as_list(foreignKey["fields"])
        pkey = _as_list(foreignKey["reference"]["fields"])
        # Check parent key constraint
        perrors = []
        if constraint is not None:
            if constraint.lower() == "uniquekey":
                perrors = check_unique_keys(parent, [pkey])
            elif constraint.lower() == "primarykey":
                perrors = check_primary_key(parent, pkey)
        if perrors and parent is not child:
            for e in enumerate(perrors):
                if "fieldName" in e:
                    e["fieldName"] = parent_name + "." + e["fieldName"]
                else:
                    e = ForeignKeyError(
                        reference=parent_name, foreignKey=foreignKey, values=e["values"]
                    )
                errors.append(e)
        # Check local key in parent key (or has null values)
        if len(ckey) == 1:
            x, y = child[ckey], parent[pkey]
            invalid = ~(x.iloc[:, 0].isin(y.iloc[:, 0]) | x.iloc[:, 0].isna())
        else:
            key = range(len(ckey))
            x, y = child[ckey].set_axis(key, axis=1), parent[pkey].set_axis(key, axis=1)
            invalid = ~(
                pd.concat([y, x]).duplicated().iloc[len(y) :] | x.isna().any(axis=1)
            )
        if invalid.any():
            errors.append(
                ForeignKeyError(
                    reference=parent_name,
                    foreignKey=foreignKey,
                    values=x[invalid].drop_duplicates().values.tolist(),
                )
            )
    return errors
