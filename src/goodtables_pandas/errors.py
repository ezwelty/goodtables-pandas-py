"""Custom error construction."""
from typing import Any, List

import frictionless


class Error(frictionless.errors.Error):
    """Generic error."""

    defaults: dict = {}

    def __init__(self: "Error", note: str = "", **kwargs: Any) -> None:
        self["code"]: str = self.code
        self["name"]: str = self.name
        self["tags"]: List[str] = self.tags
        self["note"]: str = note
        self.update({**self.defaults, **kwargs})
        self["message"]: str = self.template.format(**self)
        self["description"]: str = self.description


class TypeError(Error):
    """Field values type or format error."""

    code: str = "type-error"
    name: str = "Type Error"
    tags: List[str] = ["#body", "#schema"]
    template: str = (
        "Values for field {fieldName} "
        + 'are not type "{fieldType}" and format "{fieldFormat}"'
    )
    description: str = (
        "One or more field values do not match the field type and format."
    )
    defaults: dict = {"fieldName": "", "fieldFormat": "default"}


class ConstraintTypeError(Error):
    """Field constraint type or format error."""

    code: str = "constraint-type-error"
    name: str = "Constraint Type Error"
    tags: List[str] = ["#body", "#schema"]
    template: str = (
        'Constraint {constraintName}: "{constraintValue}" for field {fieldName} '
        + 'is not type "{fieldType}" and format "{fieldFormat}"'
    )
    description: str = "A field constraint does not match the field type and format."
    defaults: dict = {"fieldName": "", "fieldFormat": "default"}


class ConstraintError(Error):
    """Field constraint error."""

    code: str = "constraint-error"
    name: str = "Constraint Error"
    tags: List[str] = ["#body", "#schema"]
    template: str = (
        "Values for field {fieldName} do not conform to "
        + 'constraint {constraintName}: "{constraintValue}"'
    )
    description: str = "One or more field values do not conform to a field constraint."
    defaults: dict = {"fieldName": ""}


class PrimaryKeyError(Error):
    """Primary key error."""

    code: str = "primary-key-error"
    name: str = "PrimaryKey Error"
    tags: List[str] = ["#body", "#schema", "#integrity"]
    template: str = "Rows do not conform to the primary key constraint: {primaryKey}"
    description: str = (
        "Values of the primary key fields should be unique for every row."
    )


class UniqueKeyError(Error):
    """Unique key error."""

    code: str = "unique-key-error"
    name: str = "UniqueKey Error"
    tags: List[str] = ["#body", "#schema", "#integrity"]
    template: str = "Rows do not conform to the unique key constraint: {uniqueKey}"
    description: str = "Values of the unique key fields should be unique for every row."


class ForeignKeyError(Error):
    """Foreign key error."""

    code: str = "foreign-key-error"
    name: str = "ForeignKey Error"
    tags: List[str] = ["#body", "#schema", "#integrity"]
    template: str = (
        "Rows in table {reference} "
        + "do not conform to the foreign key constraint: {foreignKey}"
    )
    description: str = (
        "Values of the foreign key fields should be in the reference table."
    )
