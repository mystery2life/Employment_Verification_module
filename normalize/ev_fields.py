"""
normalize.ev_fields
-------------------
Per-field normalizers for values coming from the employment verification adapter.
Also includes a small dispatcher to map EV raw keys to canonical keys and
apply the correct normalizer.
"""

from .common import (
    squash_spaces, parse_date, to_float, titlecase_job, strip_prefix
)
from .validators import is_valid_ein


def norm_employee_name_ev(item: dict) -> dict:
    v = squash_spaces((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_employer_name_ev(item: dict) -> dict:
    v = squash_spaces((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_employer_address_ev(item: dict) -> dict:
    v = squash_spaces((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_ein_ev(item: dict) -> dict:
    raw = (item or {}).get("value")
    digits = "".join(ch for ch in str(raw) if ch.isdigit()) if raw else None
    if digits and is_valid_ein(digits):
        return {"value": digits, "confidence": item.get("confidence")}
    return {"value": None, "confidence": item.get("confidence")}


def norm_hire_date_ev(item: dict) -> dict:
    v = parse_date((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_job_title_ev(item: dict) -> dict:
    v = titlecase_job((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_total_hours_ev(item: dict) -> dict:
    v = to_float((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_lof_date_ev(item: dict) -> dict:
    v = parse_date((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_lof_reason_ev(item: dict) -> dict:
    v = (item or {}).get("value")
    v = strip_prefix(v, ["Reason:", "reason:", "Reason -", "Reason –"])
    v = squash_spaces(v)
    return {"value": v, "confidence": item.get("confidence")}


def norm_last_paycheck_date_ev(item: dict) -> dict:
    v = parse_date((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}
