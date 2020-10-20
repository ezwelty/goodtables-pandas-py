# goodtables-pandas-py
[![tests](https://github.com/ezwelty/goodtables-pandas-py/workflows/tests/badge.svg)](https://github.com/ezwelty/goodtables-pandas-py/actions?workflow=tests)
[![coverage](https://codecov.io/gh/ezwelty/goodtables-pandas-py/branch/master/graph/badge.svg)](https://codecov.io/gh/ezwelty/goodtables-pandas-py)
[![pypi](https://img.shields.io/pypi/v/goodtables-pandas-py.svg)](https://pypi.org/project/goodtables-pandas-py/)

_Warning: Not an official [frictionlessdata](https://github.com/frictionlessdata) package_

This package reads and validates a Frictionless Data [Tabular Data Package](https://frictionlessdata.io/specs/tabular-data-package/) using [pandas](https://github.com/pandas-dev/pandas). It is about ~10x faster than the official [frictionlessdata/frictionless-py](https://github.com/frictionlessdata/frictionless-py), at the expense of higher memory usage.

## Usage

```bash
pip install goodtables-pandas-py
```

```python
import goodtables_pandas as goodtables

report = goodtables.validate(source='datapackage.json')
```

## Implementation notes

### Limitations

- Only fields of type `string`, `number`, `integer`, `boolean`, `date`, `datetime`, `year`, and `geopoint` are currently supported. Other types can easily be supported with additional `parse_*` functions in `parse.py`.
- Memory use could be greatly minimized by reading, parsing, and checking tables in chunks (using `pandas.read_csv(chunksize=)`), and storing only field values for unique and foreign key checks.

### Uniqueness of `null`

Pandas chooses to treat missing values (`null`) as regular values, meaning that they are equal to themselves. How uniqueness is defined as a result is illustrated in the following examples.

| unique | not unique |
| --- | --- |
| `(1)`, `(null)` | `(1)`, `(null)`, `(null)` |
| `(1, 1)`, `(1, null)` | `(1, 1)`, `(1, null)`, `(1, null)` |

As the following script demonstrates, pandas considers the repeated rows `(1, null)` to be duplicates, and thus not unique.

```python
import pandas
import numpy as np

pandas.DataFrame(dict(x=[1, 1, 1], y=[1, np.nan, np.nan])).duplicated()
```

> 0 False
1 False
2 True
dtype: bool

Although this behavior matches some SQL implementations (namely Microsoft SQL Server), others (namely PostgreSQL and SQLite) choose to treat `null` as unique. See this [dbfiddle](https://dbfiddle.uk/?rdbms=postgres_12&fiddle=8b23d68d139a715e003fe4b012e43e6a).

### Field constraints

#### `pattern`

Support for `pattern` is extended beyond `string` to all field types by testing physical values (e.g. string `"123"`) before they are parsed into their logical representation (e.g. integer `123`). See https://github.com/frictionlessdata/specs/issues/641.

#### `maxLength`, `minLength`

Support for `maxLength` and `minLength` is extended beyond collections (`string`, `array`, and `object`) to field types using the same strategy as for `pattern`.

### Key constraints

#### `primaryKey`: `primary-key-constraint`

Fields in `primaryKey` cannot contain missing values (equivalent to `required: true`).

See https://github.com/frictionlessdata/specs/issues/593.

#### `uniqueKey`: `unique-key-constraint`

The `uniqueKeys` property provides support for one or more row uniqueness
constraints which, unlike `primaryKey`, do support `null` values. Uniqueness is determined as described above.

```json
{
  "uniqueKeys": [
    ["x", "y"],
    ["y", "z"]
  ]
}
```

See https://github.com/frictionlessdata/specs/issues/593.

#### `foreignKey`: `foreign-key-constraint`

The reference key of a `foreignKey` must meet the requirements of `uniqueKey`: it must be unique but can contain `null`. The local key must be present in the reference key, unless one of the fields is null.

| reference | local: valid | local: invalid |
| --- | --- | --- |
| `(1)` | `(1)`, `(null)` | `(2)` |
| `(1)`, `(null)` | `(1)`, `(null)` | `(2)` |
| `(1, 1)` | `(1, 1)`, `(1, null)`, `(2, null)` | `(1, 2)`

#### De-duplication of key constraints

To avoid duplicate key checks, the various key constraints are expanded as follows:

- Reference foreign keys (`foreignKey.reference.fields`) are added (if not already present) to the unique keys (`uniqueKeys`) of the reference resource. The `foreignKey` check only considers whether the local key is in the reference key.
- The primary key (`primaryKey`) is moved (if not already present) to the unique keys (`uniqueKeys`) and the fields in the key become required (`field.constraints.required: true`) if not already.
- Single-field unique keys (`uniqueKeys`) are dropped and the fields become unique (`field.constraints.unique: true`) if not already.

The following example illustrates the transformation in terms of Table Schema descriptor.

**Original**

```json
{
  "fields": [
    {
      "name": "x",
      "required": true
    },
    {
      "name": "y",
      "required": true
    },
    {
      "name": "x2"
    }
  ],
  "primaryKey": ["x", "y"],
  "uniqueKeys": [
    ["x", "y"],
    ["x"]
  ],
  "foreignKeys": [
    {
      "fields": ["x2"],
      "reference": {
        "resource": "",
        "fields": ["x"]
      }
    }
  ]
}
```

**Checked**

```json
{
  "fields": [
    {
      "name": "x",
      "required": true,
      "unique": true
    },
    {
      "name": "y",
      "required": true
    },
    {
      "name": "x2"
    }
  ],
  "uniqueKeys": [
    ["x", "y"]
  ],
  "foreignKeys": [
    {
      "fields": ["x2"],
      "reference": {
        "resource": "",
        "fields": ["x"]
      }
    }
  ]
}
```
