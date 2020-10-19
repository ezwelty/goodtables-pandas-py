"""Custom error construction."""
from typing import Any, Iterable

import goodtables


def type_or_format_error(
    message: str = "Values in {name} are not type: {type} and format: {format}",
    name: str = "field",
    type: str = "string",
    format: str = "default",
    values: Iterable = None,
) -> goodtables.Error:
    """
    Error for field type or format checks.

    Arguments:
        message: String with substitutions called on other arguments (e.g. '{name}').
        name: Field name.
        type: Field type.
        format: Field format.
        values: Invalid field values.

    Returns:
        Error with code 'type-or-format-error'.
    """
    data = dict(name=name, type=type, format=format, values=values)
    return goodtables.Error(
        code="type-or-format-error", message=message, message_substitutions=data
    )


def constraint_type_or_format_error(
    value: Any,
    constraint: str = "constraint",
    name: str = "field",
    type: str = "string",
    format: str = "default",
    message: str = "Constraint {constraint}: {value} for {name} is not type: {type} and format: {format}",  # noqa: E501
) -> goodtables.Error:
    """
    Error for field constraint type or format checks.

    Arguments:
        value: Constraint value.
        constraint: Constraint type.
        name: Field name.
        type: Field type.
        format: Field format.
        message: String with substitutions called on other arguments (e.g. '{name}').

    Returns:
        Error with code 'type-or-format-error'.
    """
    data = dict(name=name, constraint=constraint, value=value, type=type, format=format)
    return goodtables.Error(
        code="type-or-format-error", message=message, message_substitutions=data
    )


def constraint_error(
    code: str,
    constraint: str,
    value: Any,
    values: Iterable = None,
    name: str = "field",
    message: str = "Values in {name} violate constraint {constraint}: {value}",
) -> goodtables.Error:
    """
    Error for field constraint checks.

    Arguments:
        code: Error code.
        constraint: Constraint type.
        value: Constraint value.
        values: Invalid field values.
        name: Field name.
        message: String with substitutions called on other arguments (e.g. '{name}').

    Returns:
        Error with code `code`.
    """
    data = dict(name=name, constraint=constraint, value=value, values=values)
    return goodtables.Error(code=code, message=message, message_substitutions=data)


def key_error(
    code: str,
    constraint: str,
    value: Any,
    message: str = "Rows violate {constraint}: {value}",
    values: Iterable = None,
) -> goodtables.Error:
    """
    Error for table key constraint.

    Arguments:
        code: Error code.
        constraint: Constraint type.
        value: Constraint value.
        message: String with substitutions called on other arguments (e.g. '{name}').
        values: Invalid key values.

    Returns:
        Error with code `code`.
    """
    data = dict(constraint=constraint, value=value, values=values)
    return goodtables.Error(code=code, message=message, message_substitutions=data)


def foreign_key_error(
    code: str,
    constraint: str,
    value: dict,
    message: str = "Rows in {value['reference']['resource']} violate {constraint}: {value}",  # noqa: E501
    values: Iterable = None,
) -> goodtables.Error:
    """
    Error for table foreign key constraint.

    Arguments:
        code: Error code.
        constraint: Constraint type.
        value: Constraint value.
        message: String with substitutions called on other arguments (e.g. '{name}').
        values: Invalid key values.

    Returns:
        Error with code `code`.
    """
    data = dict(constraint=constraint, value=value, values=values)
    return goodtables.Error(code=code, message=message, message_substitutions=data)
