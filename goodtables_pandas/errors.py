import goodtables

def type_or_format_error(
    message="Values in {name} are not type: {type} and format: {format}",
    name='field', type='string', format='default', values=None):
    data = dict(
        name=name, type=type, format=format, values=values)
    return goodtables.Error(
        code='type-or-format-error',
        message=message, message_substitutions=data)

def constraint_type_or_format_error(
    value, constraint='constraint', name='field', type='string', format='default',
    message="Constraint {constraint}: {value} for {name} is not type: {type} and format: {format}"):
    data = dict(
        name=name, constraint=constraint, value=value, type=type, format=format)
    return goodtables.Error(
        code='type-or-format-error',
        message=message, message_substitutions=data)

def constraint_error(
    code, constraint, value, values=None, name='field',
    message="Values in {name} violate constraint {constraint}: {value}"):
    data = dict(
        name=name, constraint=constraint, value=value, values=values)
    return goodtables.Error(
        code=code, message=message, message_substitutions=data)

def key_error(
    code, constraint, value,
    message="Rows violate {constraint}: {value}",
    values=None):
    data = dict(
        constraint=constraint, value=value, values=values)
    return goodtables.Error(
        code=code, message=message, message_substitutions=data)

def foreign_key_error(
    code, constraint, value,
    message="Rows in {value['reference']['resource']} violate {constraint}: {value}",
    values=None):
    data = dict(
        constraint=constraint, value=value, values=values)
    return goodtables.Error(
        code=code, message=message, message_substitutions=data)
