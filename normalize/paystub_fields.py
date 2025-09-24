"""
normalize.paystub_fields
------------------------
Per-field normalizers for values coming from the paystub adapter.
Each function receives a dict like {"value": <raw>, "confidence": <float>}
and returns the same shape with cleaned value.

These functions never raise. If cleaning fails, value becomes None (confidence kept).
"""

from .common import squash_spaces, clean_money, parse_date, to_float, titlecase_job


def _keep(shape):
    """Internal helper: ensure dict with keys 'value' and 'confidence'."""
    val = shape.get("value")
    return {"value": val, "confidence": shape.get("confidence")}


def norm_employee_name_ps(item: dict) -> dict:
    v = squash_spaces((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_employer_name_ps(item: dict) -> dict:
    v = squash_spaces((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_employer_address_ps(item: dict) -> dict:
    v = squash_spaces((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_ein_ps(item: dict) -> dict:
    # Some stubs don’t include EIN; just return as-is (merge will fallback to EV).
    return _keep(item or {})


def norm_job_title_ps(item: dict) -> dict:
    v = titlecase_job((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_pay_date_ps(item: dict) -> dict:
    v = parse_date((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_gross_amount_ps(item: dict) -> dict:
    v = clean_money((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_total_hours_ps(item: dict) -> dict:
    v = to_float((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_period_start_ps(item: dict) -> dict:
    v = parse_date((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}


def norm_period_end_ps(item: dict) -> dict:
    v = parse_date((item or {}).get("value"))
    return {"value": v, "confidence": item.get("confidence")}
