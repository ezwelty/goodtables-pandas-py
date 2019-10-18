import pandas
import goodtables
from .errors import (constraint_error, key_error, foreign_key_error)
from .parse import parse_field_constraint

# ---- Field constraints ----

def check_constraints(df, schema):
    errors = []
    for field in schema.get('fields', []):
        constraints = field.get('constraints', {})
        result = check_field_constraints(
            df[field['name']], **constraints, field=field)
        if result:
            errors += result
    return errors

def check_field_constraints(
    x, required=False, unique=False, minLength=None,
    maxLength=None, minimum=None, maximum=None, pattern=None, enum=None,
    field={}):
    name = field.get('name', 'field')
    type = field.get('type', 'string')
    errors = []
    if required and x.isna().any():
        errors.append(constraint_error(
            name=name, code='required-constraint', constraint='required',
            value=required, values=[float('nan')]))
    if unique:
        # NOTE: Pandas considers nulls equal (not unique)
        invalid = x.duplicated()
        if invalid.any():
            errors.append(constraint_error(
                name=name, code='unique-constraint', constraint='unique',
                value=unique, values=list(x[invalid].unique())))
    x = x.dropna()
    length_types = ('string', 'array', 'object')
    if minLength is not None and type in length_types:
        invalid = x.str.len() < minLength
        if invalid.any():
            errors.append(constraint_error(
                name=name, code='minimum-length-constraint', constraint='minLength',
                value=minLength, values=list(x[invalid].unique())))
    if maxLength is not None and type in length_types:
        invalid = x.str.len() > maxLength
        if invalid.any():
            errors.append(constraint_error(
                name=name, code='maximum-length-constraint', constraint='minLength',
                value=maxLength, values=list(x[invalid].unique())))
    minmax_types = (
        'integer', 'number', 'date', 'time', 'datetime', 'year', 'yearmonth')
    if minimum is not None:
        minimum = parse_field_constraint(minimum, 'minimum', **field)
        if isinstance(minimum, goodtables.Error):
            errors.append(minimum)
        else:
            invalid = x < minimum
            if invalid.any():
                errors.append(constraint_error(
                    name=name, code='minimum-constraint', constraint='minimum',
                    value=minimum, values=list(x[invalid].unique())))
    if maximum is not None:
        maximum = parse_field_constraint(maximum, 'maximum', **field)
        if isinstance(maximum, goodtables.Error):
            errors.append(maximum)
        else:
            invalid = x > maximum
            if invalid.any():
                errors.append(constraint_error(
                    name=name, code='maximum-constraint', constraint='maximum',
                    value=maximum, values=list(x[invalid].unique())))
    if pattern and type in ('string', ):
        invalid = ~x.str.contains(pattern)
        if invalid.any():
            errors.append(constraint_error(
                name=name, code='pattern-constraint', constraint='pattern',
                value=pattern, values=list(x[invalid].unique())))
    if enum:
        enum = parse_field_constraint(enum, 'enum', **field)
        if isinstance(enum, goodtables.Error):
            errors.append(enum)
        else:
            invalid = ~x.isin(enum)
            if invalid.any():
                errors.append(constraint_error(
                    name=name, code='enumerable-constraint', constraint='enum',
                    value=enum, values=list(x[invalid].unique())))
    return errors

# ---- Key constraints ----

def _as_list(x):
    if not isinstance(x, list):
        x = [x]
    return x

def _check_primary_key_required(df, primaryKey):
    errors = []
    key = _as_list(primaryKey)
    for name in key:
        errors += check_field_constraints(
            df[name], required=True, field=dict(name=name))
    return errors

def check_primary_key(df, primaryKey, skip_required=False, skip_single=False):
    errors = []
    key = _as_list(primaryKey)
    if key:
        if not skip_required:
            errors += _check_primary_key_required(df, primaryKey)
        if skip_single and len(key) < 2:
            return errors
        invalid = df.duplicated(subset=key)
        if invalid.any():
            errors.append(key_error(
                code='primary-key-constraint', constraint='primaryKey',
                value=key,
                values=df[key][invalid].drop_duplicates().values.tolist()))
    return errors

def check_unique_keys(df, uniqueKeys, skip_single=False):
    errors = []
    for uniqueKey in uniqueKeys:
        key = _as_list(uniqueKey)
        if skip_single and len(key) < 2:
            continue
        invalid = df.duplicated(subset=key)
        if invalid.any():
            errors.append(key_error(
                code='unique-key-constraint', constraint='uniqueKey',
                value=key,
                values=df[key][invalid].drop_duplicates().values.tolist()))
    return errors

def check_foreign_keys(df, foreignKeys, references={}, constraint=None):
    errors = []
    child = df
    for foreignKey in foreignKeys:
        parent_name = foreignKey['reference']['resource']
        if parent_name == '':
            parent = child
        else:
            if parent_name in references:
                parent = references[parent_name]
            else:
                continue
        ckey = _as_list(foreignKey['fields'])
        pkey = _as_list(foreignKey['reference']['fields'])
        # Check parent key constraint
        perrors = []
        if constraint is not None:
            if constraint.lower() == 'uniquekey':
                perrors = check_unique_keys(parent, [pkey])
            elif constraint.lower() == 'primarykey':
                perrors = check_primary_key(parent, pkey)
        if perrors and parent is not child:
            for e in enumerate(perrors):
                if 'name' in e._message_substitutions:
                    name = e._message_substitutions['name']
                    e._message_substitutions['name'] = parent_name + '.' + name
                else:
                    e = foreign_key_error(
                        code='foreign-key-constraint',
                        constraint='foreignKey',
                        value=foreignKey,
                        values=e._message_substitutions['values'])
                errors.append(e)
        # Check local key in parent key (or has null values)
        x, y = child[ckey], parent[pkey]
        if len(ckey) == 1:
            invalid = ~(x.ix[:, 0].isin(y.ix[:, 0]) | x.ix[:, 0].isna())
        else:
            invalid = ~(pandas.concat([y, x]).duplicated().iloc[len(y):] |
                x.isna().any(axis=1))
        if invalid.any():
            errors.append(key_error(
                code='foreign-key-constraint', constraint='foreignKey',
                value=foreignKey,
                values=x[invalid].drop_duplicates().values.tolist()))
    return errors
