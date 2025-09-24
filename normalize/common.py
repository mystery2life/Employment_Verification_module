"""
normalize.common
----------------
Low-level helpers shared by paystub/EV normalizers.
All helpers are pure (no I/O) and should never raise on bad input.
"""

from __future__ import annotations
import re
from datetime import datetime

_MONEY_RX = re.compile(r"[^\d.,-]")
_ONLY_DIGITS = re.compile(r"\D+")


def squash_spaces(s: str | None) -> str | None:
    """Collapse extra spaces/newlines and trim. Returns None if empty."""
    if not s:
        return None
    out = " ".join(str(s).split())
    return out or None


def clean_money(s: str | None) -> str | None:
    """
    Fix common OCR artifacts in currency strings.
    Examples:
      "$3, 461. 54" -> "$3,461.54"
      "$ 6500"      -> "$6,500" (we do not insert comma; we just normalize spaces)
    """
    if not s:
        return None
    s = squash_spaces(s) or s
    # join separated thousands and decimals like "3, 461. 54" -> "3,461.54"
    s = s.replace(", ", ",").replace(" .", ".").replace(". ", ".").replace(" ,", ",")
    # ensure "$ " -> "$"
    s = s.replace("$ ", "$")
    return s


def money_to_float(s: str | None) -> float | None:
    """Extract a numeric float from a currency string. Returns None if fails."""
    if not s:
        return None
    digits = _MONEY_RX.sub("", s)
    if not digits:
        return None
    try:
        # Replace commas carefully; keep last '.' as decimal point
        return float(digits.replace(",", ""))
    except Exception:
        return None


def to_float(s: str | int | float | None) -> float | None:
    """Parse a number-like value to float, else None."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = squash_spaces(str(s))
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        # Extract first number if the string contains words+number
        m = re.search(r"-?\d+(\.\d+)?", s)
        return float(m.group(0)) if m else None


def parse_date(s: str | None) -> str | None:
    """
    Parse many common date formats into 'YYYY-MM-DD'. Returns None if invalid.
    Rejects suspicious very-short tokens (e.g., "11").
    """
    if not s:
        return None
    txt = squash_spaces(str(s))
    if not txt or len(txt) < 6:   # crude guard against things like "11"
        return None

    # Try a few common formats first
    fmts = ["%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m/%d/%y", "%m-%d-%y", "%d-%b-%Y", "%d %b %Y"]
    for f in fmts:
        try:
            dt = datetime.strptime(txt, f)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    # Fallback: extract digits in order and attempt M/D/Y
    m = re.findall(r"\d{1,4}", txt)
    if len(m) >= 3:
        try:
            mm, dd, yyyy = int(m[0]), int(m[1]), int(m[2]) if len(m[2]) == 4 else 2000 + int(m[2])
            dt = datetime(year=yyyy, month=mm, day=dd)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None
    return None


def strip_prefix(s: str | None, prefixes: list[str]) -> str | None:
    """Remove any leading label among `prefixes` (case-insensitive)."""
    if not s:
        return None
    txt = s.lstrip()
    lowered = txt.lower()
    for p in prefixes:
        if lowered.startswith(p.lower()):
            return txt[len(p):].lstrip()
    return txt


def titlecase_job(s: str | None) -> str | None:
    """
    Simple title-casing for job titles, preserving all-caps words (e.g., 'CEO').
    """
    if not s:
        return None
    s = squash_spaces(s) or s
    parts = s.split()
    out = []
    for w in parts:
        out.append(w if w.isupper() and len(w) <= 4 else w.capitalize())
    return " ".join(out)
