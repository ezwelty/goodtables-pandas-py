"""Configuration options."""

raise_first_invalid_integer = False
"""
bool: Whether to only report the first invalid value of an integer field.
  Provides a large speed increase at the expense of a less informative error.
  Only used if `bareNumber` is `True` (the default).
"""

raise_first_invalid_number = False
"""
bool: Whether to only report the first invalid value of a number field.
  Provides a large speed increase at the expense of a less informative error.
  Only used if `bareNumber` is `True` (the default).
"""
