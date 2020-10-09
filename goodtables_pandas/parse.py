import pandas
import goodtables
from .errors import (type_or_format_error, constraint_type_or_format_error)

def parse_table(df, schema):
    errors = []
    for field in schema.get('fields', []):
        result = parse_field(df[field['name']], **field)
        if isinstance(result, goodtables.Error):
            result._message_substitutions['name'] = field['name']
            errors.append(result)
        else:
            df[field['name']] = result
    return errors or df

def parse_field(x, type='string', **field):
    parser = globals().get('parse_' + type, None)
    if not parser:
        raise NotImplementedError(
            'Field type: ' + type + ' not supported')
    argnames = parser.__code__.co_varnames[1:parser.__code__.co_argcount]
    field = {key: field[key] for key in argnames if key in field}
    return parser(x, **field)

def parse_field_constraint(x, constraint, type='string', **field):
    is_list = isinstance(x, list)
    X = pandas.Series(x)
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

def parse_string(x, format='default'):
    pattern = None
    if format == 'email':
        # https://emailregex.com/
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    elif format == 'uri':
        # https://en.wikipedia.org/wiki/Uniform_Resource_Identifier
        # https://www.regextester.com/94092
        pattern = r"^\w+:(\/?\/?)[^\s]+$"
    elif format == 'binary':
        # https://stackoverflow.com/questions/475074/regex-to-parse-or-validate-base64-data
        pattern = r"[^-A-Za-z0-9+/=]|=[^=]|={3,}$"
    elif format == 'uuid':
        # https://en.wikipedia.org/wiki/Universally_unique_identifier
        pattern = r"[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}"
    if pattern:
        invalid = ~x.str.contains(pattern)
        if invalid.any():
            return type_or_format_error(
                type='string', format=format,
                values=invalid.dropna().unique().tolist())
    return x

def parse_number(x, decimalChar='.', groupChar=None, bareNumber=True):
    if groupChar:
        x = x.str.replace(groupChar, '')
    if decimalChar != '.':
        x = x.str.replace(decimalChar, '.')
    if not bareNumber:
        number = r"(nan|-?inf|-?[0-9\.]+(?:e[+-]?[0-9\.]+)?)"
        x = x.str.lower().str.extract(number, expand=False)
    try:
        return x.astype(float)
    except ValueError as e:
        return type_or_format_error(message=str(e), type='number')

def parse_integer(x, bareNumber=True):
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
    x, trueValues=('true', 'True', 'TRUE', '1'),
    falseValues=('false', 'False', 'FALSE', '0')):
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
