"""Validate tabular data packages."""
import time
from typing import Any, Dict, Tuple, Union

import frictionless
import pandas as pd
from typing_extensions import Literal

from .check import (
    _as_list,
    check_constraints,
    check_foreign_keys,
    check_primary_key,
    check_unique_keys,
)
from .parse import parse_table
from .read import read_table


def validate(  # noqa: C901
    source: Union[str, dict],
    source_type: Literal["package"] = "package",
    return_tables: bool = False,
    **options: Any,
) -> Union[frictionless.Report, Tuple[frictionless.Report, Dict[str, pd.DataFrame]]]:
    """
    Validate a Tabular Data Package.

    This is a wrapper of :func:`frictionless.validate`:
    https://frictionlessdata.io/tooling/python/api-reference/#frictionless-validate

    Arguments:
        source: Path to, or content of, a Tabular Data Package descriptor.
        source_type: Souce type (currently limited to "package").
        return_tables: Whether to return the tables read and parsed during validation.
        **options: Optional arguments to :func:`frictionless.validate_package` and
            :func:`frictionless.validate_table`.

    Raises:
        NotImplementedError: Source type not supported.

    Returns:
        An error report and (if `return_tables=True`) the tables.
    """
    if source_type != "package":
        raise NotImplementedError(f"source_type {source_type} not supported")
    # Start clock
    start = time.time()
    # Initialize report
    options = {
        # Non-header rows are checked with pandas (limit_rows=0 not permitted)
        "query": frictionless.Query(limit_rows=1),
        "skip_errors": ["#body"],
        # Foreign key checks are performed with pandas
        "nolookup": True,
        # Use existing schema rather than inferring one from a data sample
        "noinfer": True,
        # Multiprocessing not worth overhead for metadata and header checks
        "nopool": True,
        **options,
    }
    report = frictionless.validate(source=source, source_type=source_type, **options)
    # Load resource descriptors (report descriptors missing resource name)
    resources = frictionless.Package(source).get("resources", [])
    names = [resource["name"] for resource in resources]
    # Standardize format of resource schema attributes
    for resource in resources:
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
    for resource in resources:
        schema = resource["schema"]
        # foreignKey.reference: Add to reference.uniqueKeys
        foreignKeys = schema.get("foreignKeys", [])
        for foreignKey in foreignKeys:
            key = foreignKey["reference"]["fields"]
            parent = foreignKey["reference"]["resource"] or resource["name"]
            i = names.index(parent)
            keys = resources[i]["schema"].get("uniqueKeys", [])
            keys.append(key)
            resources[i]["schema"]["uniqueKeys"] = [
                list(t) for t in set(tuple(k) for k in keys)
            ]
    for resource in resources:
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
    for i, resource in enumerate(resources):
        table_start = time.time()
        # Table body is not checked if table failed initial check
        if not report["tables"][i]["valid"]:
            continue
        # Read table
        # Pull resolved relative paths from report
        paths = _as_list(report["tables"][i].get("path", ""))
        result = read_table(resource, path=paths)
        if isinstance(result, list):
            report["tables"][i]["errors"] += result
            continue
        # Parse table
        report["tables"][i]["scope"] += ["type-error"]
        result = parse_table(result, schema=resource.get("schema", {}))
        if isinstance(result, list):
            report["tables"][i]["errors"] += result
            continue
        # Check field constraints and table keys
        report["tables"][i]["scope"] += [
            "constraint-error",
            "unique-error",
            "primary-key-error",
        ]
        name = resource["name"]
        dfs[name] = result
        errors = (
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
        report["tables"][i]["stats"]["rows"] = len(dfs[name])
        # Remove row limit used for initial report
        report["tables"][i]["query"] = {}
        report["tables"][i]["time"] += time.time() - table_start
    # Check foreign keys
    for i, resource in enumerate(resources):
        table_start = time.time()
        name = resource["name"]
        if name not in dfs:
            # Skip check if table was invalid
            continue
        errors = check_foreign_keys(
            dfs[name],
            resource.get("schema", {}).get("foreignKeys", []),
            references=dfs,
            constraint=None,
        )
        report["tables"][i]["errors"] += errors
        report["tables"][i]["time"] += time.time() - table_start
        report["tables"][i]["scope"] += ["foreign-key-error"]
    # Update report
    table_errors = 0
    for i, table in enumerate(report["tables"]):
        nerrors = len(table["errors"])
        table["stats"]["errors"] = nerrors
        table["valid"] = nerrors == 0
        table_errors += nerrors
    total_errors = len(report["errors"]) + table_errors
    report["stats"]["errors"] = total_errors
    report["valid"] = not total_errors
    report["time"] = time.time() - start
    # Return report
    if return_tables:
        return report, dfs
    return report
