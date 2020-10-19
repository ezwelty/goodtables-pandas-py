"""Validate tabular data packages."""
import datetime
import math
import re
from typing import Dict, Tuple, Union

import datapackage
import goodtables
import pandas as pd

from .check import (
    _as_list,
    check_constraints,
    check_field_constraints,
    check_foreign_keys,
    check_primary_key,
    check_unique_keys,
)
from .parse import parse_table
from .read import read_table


def validate(  # noqa: C901
    source: Union[str, dict], return_tables: bool = False
) -> Union[dict, Tuple[dict, Dict[str, pd.DataFrame]]]:
    """
    Validate Tabular Data Package.

    Arguments:
        source: Path to or content of a Tabular Data Package descriptor
            (https://specs.frictionlessdata.io/tabular-data-package).
        return_tables: Whether to return the tables read and parsed during validation.

    Returns:
        An error report and (if `return_tables=True`) the tables.
    """
    # Start clock
    start = datetime.datetime.now()
    # Initialize report
    checks = [
        "blank-header",
        "duplicate-header",
        "non-matching-header",
        "extra-header",
        "missing-header",
    ]
    report = goodtables.validate(
        source=source,
        preset="datapackage",
        checks=checks,
        table_limit=math.inf,
        row_limit=0,
    )
    # Remove row_limit warnings
    report["warnings"] = [
        w for w in report["warnings"] if re.match(r"row\(s\) limit", w)
    ]
    # Retrieve descriptor
    package = datapackage.Package(source).descriptor
    resources = package.get("resources", [])
    names = [resource["name"] for resource in resources]
    # Expand descriptor
    for resource, name in zip(resources, names):
        schema = resource["schema"]
        if "primaryKey" in schema:
            schema["primaryKey"] = _as_list(schema["primaryKey"])
        if "uniqueKeys" in schema:
            schema["uniqueKeys"] = [_as_list(k) for k in schema["uniqueKeys"]]
        foreignKeys = schema.get("foreignKeys", [])
        for foreignKey in foreignKeys:
            foreignKey["fields"] = _as_list(foreignKey["fields"])
            foreignKey["reference"]["fields"] = _as_list(
                foreignKey["reference"]["fields"]
            )
    # Remove duplicate key checks
    for resource, name in zip(resources, names):
        schema = resource["schema"]
        # foreignKey.reference: Add to reference.uniqueKeys
        foreignKeys = schema.get("foreignKeys", [])
        for foreignKey in foreignKeys:
            key = foreignKey["reference"]["fields"]
            parent = foreignKey["reference"]["resource"] or name
            i = names.index(parent)
            keys = resources[i]["schema"].get("uniqueKeys", [])
            keys.append(key)
            resources[i]["schema"]["uniqueKeys"] = [
                list(t) for t in set(tuple(k) for k in keys)
            ]
    for resource, name in zip(resources, names):
        required, unique = [], []
        schema = resource["schema"]
        # primaryKey: Move to field.constraint.required, uniqueKey
        primaryKey = schema.get("primaryKey", [])
        if primaryKey:
            required += primaryKey
            keys = schema.get("uniqueKeys", [])
            keys.append(primaryKey)
            schema["uniqueKeys"] = [list(t) for t in set(tuple(k) for k in keys)]
            schema.pop("primaryKey")
        # uniqueKey: Move to field unique (if single)
        uniqueKeys = schema.get("uniqueKeys", [])
        for i, uniqueKey in reversed(list(enumerate(uniqueKeys.copy()))):
            if len(uniqueKey) == 1:
                unique += uniqueKey
                uniqueKeys.pop(i)
        # Update field constraints
        for field in schema["fields"]:
            field["constraints"] = field.get("constraints", {})
            if field["name"] in required:
                field["constraints"]["required"] = True
            if field["name"] in unique:
                field["constraints"]["unique"] = True
    # Read and parse tables
    dfs = {}
    for i, resource in enumerate(package.get("resources", [])):
        # Skip if header error
        if not report["tables"][i]["valid"]:
            continue
        errors = []
        # Read table
        # Pull resolved paths from goodtables
        paths = _as_list(report["tables"][i].get("source", ""))
        result = read_table(resource, path=paths)
        if isinstance(result, list):
            errors += result
            report["tables"][i]["errors"] += errors
            continue
        # Before parsing, run checks on:
        # constraint: pattern | type: ~string
        # constraint: minLength, maxLength | type: ~(string, array, object)
        for field in resource.get("schema", {}).get("fields", []):
            constraints = field.get("constraints", {})
            x = result[field.get("name", None)]
            if field.get("type", "string") not in ("string",):
                if "pattern" in constraints:
                    errors += check_field_constraints(
                        x, pattern=constraints["pattern"], field=field
                    )
            if field.get("type", "string") not in ("string", "array", "object"):
                if "minLength" in constraints:
                    errors += check_field_constraints(
                        x, minLength=constraints["minLength"], field=field
                    )
                if "maxLength" in constraints:
                    errors += check_field_constraints(
                        x, maxLength=constraints["maxLength"], field=field
                    )
        # Parse table
        result = parse_table(result, schema=resource.get("schema", {}))
        if isinstance(result, list):
            errors += result
            report["tables"][i]["errors"] += errors
            continue
        # Check table
        name = resource["name"]
        dfs[name] = result
        errors += (
            check_constraints(dfs[name], schema=resource.get("schema", {}))
            + check_primary_key(
                dfs[name],
                resource.get("schema", {}).get("primaryKey", []),
                skip_required=True,
                skip_single=True,
            )
            + check_unique_keys(
                dfs[name],
                resource.get("schema", {}).get("uniqueKeys", []),
                skip_single=True,
            )
        )
        report["tables"][i]["errors"] += errors
        report["tables"][i]["row-count"] = len(dfs[name])
    # Check foreign keys
    for i, resource in enumerate(package.get("resources", [])):
        name = resource["name"]
        if name not in dfs:
            continue
        errors = check_foreign_keys(
            dfs[name],
            resource.get("schema", {}).get("foreignKeys", []),
            references=dfs,
            constraint=None,
        )
        report["tables"][i]["errors"] += errors
    # Update report
    counts = []
    for i, table in enumerate(report["tables"]):
        count = len(table["errors"])
        table["error-count"] = count
        table["valid"] = count == 0
        table["errors"] = [
            {k: v for k, v in dict(e).items() if v is not None}
            if isinstance(e, goodtables.Error)
            else e
            for e in table["errors"]
        ]
        counts.append(count)
        table.pop("time")
    report["error-count"] = sum(counts)
    report["valid"] = sum(counts) == 0
    report["time"] = datetime.datetime.now() - start
    # Return report
    if return_tables:
        return report, dfs
    return report
