"""
normalize.validators
--------------------
Optional sanity checks used by normalizers.
"""

import re

_EIN_RX = re.compile(r"^\d{6}$")


def is_valid_ein(value: str | None) -> bool:
    """Return True when value is exactly 6 digits."""
    if not value:
        return False
    return bool(_EIN_RX.match(value))
