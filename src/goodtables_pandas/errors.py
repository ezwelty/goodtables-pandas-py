from typing import Any, Iterable

import goodtables

def type_or_format_error(
    message: str = "Values in {name} are not type: {type} and format: {format}",
    name: str = 'field', type: str = 'string', format: str = 'default', values: Iterable = None) -> goodtables.Error:
    data = dict(
        name=name, type=type, format=format, values=values)
    return goodtables.Error(
        code='type-or-format-error',
        message=message, message_substitutions=data)

def constraint_type_or_format_error(
    value: Any, constraint: str = 'constraint', name: str = 'field', type: str = 'string', format: str = 'default',
    message: str = "Constraint {constraint}: {value} for {name} is not type: {type} and format: {format}") -> goodtables.Error:
    data = dict(
        name=name, constraint=constraint, value=value, type=type, format=format)
    return goodtables.Error(
        code='type-or-format-error',
        message=message, message_substitutions=data)

def constraint_error(
    code: str, constraint: str, value: Any, values: Iterable = None, name: str = 'field',
    message: str = "Values in {name} violate constraint {constraint}: {value}") -> goodtables.Error:
    data = dict(
        name=name, constraint=constraint, value=value, values=values)
    return goodtables.Error(
        code=code, message=message, message_substitutions=data)

def key_error(
    code: str, constraint: str, value: Any,
    message: str = "Rows violate {constraint}: {value}",
    values: Iterable = None) -> goodtables.Error:
    data = dict(
        constraint=constraint, value=value, values=values)
    return goodtables.Error(
        code=code, message=message, message_substitutions=data)

def foreign_key_error(
    code: str, constraint: str, value: dict,
    message: str = "Rows in {value['reference']['resource']} violate {constraint}: {value}",
    values: Iterable = None) -> goodtables.Error:
    data = dict(
        constraint=constraint, value=value, values=values)
    return goodtables.Error(
        code=code, message=message, message_substitutions=data)
