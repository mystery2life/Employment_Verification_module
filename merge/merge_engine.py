"""
merge.merge_engine
------------------
Normalizes raw extractor outputs (paystub + EV) and merges them into a single
unified JSON using hard source priority rules.

Usage:
    merged = build_unified(paystub_raw_dict, ev_raw_dict)
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, Any

from .rules import (
    CANONICAL_FIELDS, PRIORITY,
    PAYSTUB_FIELD_MAP, EV_FIELD_MAP
)
from normalize import paystub_fields as psn
from normalize import ev_fields as evn


def _shape(value, confidence):
    """Create a {value, confidence} record."""
    return {"value": value, "confidence": confidence}


# ---------- Normalization ----------

def normalize_paystub(ps: Dict[str, Dict[str, Any]] | None) -> Dict[str, Dict[str, Any]]:
    """
    Map and clean paystub fields into canonical names.
    Input:  {"RawKey": {"value": ..., "confidence": ...}, ...}
    Output: {"CanonicalKey": {"value": cleaned, "confidence": ...}, ...}
    """
    ps = ps or {}
    out: Dict[str, Dict[str, Any]] = {}

    def take(raw_key, canon_key, fn):
        item = ps.get(raw_key)
        if item is None or canon_key is None:
            return
        out[canon_key] = fn(item)

    take("EmployeeName", "EmployeeName", psn.norm_employee_name_ps)
    take("EmployerName", "EmployerName", psn.norm_employer_name_ps)
    take("EmployerAddress", "EmployerAddress", psn.norm_employer_address_ps)
    take("EIN", "EIN", psn.norm_ein_ps)
    take("JobTitle", "JobTitle", psn.norm_job_title_ps)
    take("PayDate", "PayDate", psn.norm_pay_date_ps)
    take("CurrentPeriodGrossPay", "GrossAmount", psn.norm_gross_amount_ps)
    take("TotalHoursWorked", "TotalHours", psn.norm_total_hours_ps)
    take("PayPeriodStartDate", "PayPeriodStartDate", psn.norm_period_start_ps)
    take("PayPeriodEndDate", "PayPeriodEndDate", psn.norm_period_end_ps)

    return out


def normalize_ev(ev: Dict[str, Dict[str, Any]] | None) -> Dict[str, Dict[str, Any]]:
    """
    Map and clean EV fields into canonical names.
    """
    ev = ev or {}
    out: Dict[str, Dict[str, Any]] = {}

    def take(raw_key, canon_key, fn):
        item = ev.get(raw_key)
        if item is None or canon_key is None:
            return
        out[canon_key] = fn(item)

    take("EmployeeName", "EmployeeName", evn.norm_employee_name_ev)
    take("CompanyName", "EmployerName", evn.norm_employer_name_ev)
    take("Company Address", "EmployerAddress", evn.norm_employer_address_ev)
    take("EIN", "EIN", evn.norm_ein_ev)
    take("HireDate", "HireDate", evn.norm_hire_date_ev)
    take("JobTitle", "JobTitle", evn.norm_job_title_ev)
    take("AverageWorkingHours", "TotalHours", evn.norm_total_hours_ev)
    take("EmplyomentEndDate", "LossOfEmploymentDate", evn.norm_lof_date_ev)
    take("EmploymentEndDateReason", "LossOfEmploymentReason", evn.norm_lof_reason_ev)
    take("FinalPayCheckDate", "DateOfLastPaycheck", evn.norm_last_paycheck_date_ev)

    return out


# ---------- Derivations ----------

def derive_pay_frequency(ps_norm: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]] | None:
    """
    Compute PayFrequency from PayPeriodStartDate/PayPeriodEndDate (paystub only).
    Returns {"PayFrequency": {"value": "...", "confidence": 100}} or None.
    """
    s = (ps_norm.get("PayPeriodStartDate") or {}).get("value")
    e = (ps_norm.get("PayPeriodEndDate") or {}).get("value")
    if not s or not e:
        return None
    try:
        dt_s = datetime.strptime(s, "%Y-%m-%d")
        dt_e = datetime.strptime(e, "%Y-%m-%d")
        days = (dt_e - dt_s).days + 1  # inclusive
    except Exception:
        return None

    if days <= 8:
        val = "Weekly"
    elif days <= 15:
        val = "Bi-Weekly"
    elif days <= 20:
        val = "Semi-Monthly"
    else:
        val = "Monthly"

    return {"PayFrequency": {"value": val, "confidence": 100.0}}


# ---------- Merge ----------

def merge_by_priority(ps_norm: Dict[str, Dict[str, Any]],
                      ev_norm: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Apply hard source priority for each canonical field.
    """
    final: Dict[str, Dict[str, Any]] = {}

    for field in CANONICAL_FIELDS:
        chosen = None
        for src in PRIORITY.get(field, []):
            if src == "paystub":
                item = ps_norm.get(field)
                if item and item.get("value") not in (None, ""):
                    chosen = item
                    break
            elif src == "ev":
                item = ev_norm.get(field)
                if item and item.get("value") not in (None, ""):
                    chosen = item
                    break
            elif src == "derived":
                # compute later (outside loop) to keep simple
                pass

        final[field] = chosen or {"value": None, "confidence": None}

    # Fill derived fields after loop (e.g., PayFrequency)
    if "PayFrequency" in CANONICAL_FIELDS and "derived" in PRIORITY.get("PayFrequency", []):
        d = derive_pay_frequency(ps_norm)
        if d and d.get("PayFrequency"):
            final["PayFrequency"] = d["PayFrequency"]

    return final


def build_unified(paystub_raw: Dict[str, Dict[str, Any]] | None,
                  ev_raw: Dict[str, Dict[str, Any]] | None) -> Dict[str, Any]:
    """
    Entry point: normalize both sources, merge by priority, return unified JSON.
    """
    ps_norm = normalize_paystub(paystub_raw or {})
    ev_norm = normalize_ev(ev_raw or {})
    merged = merge_by_priority(ps_norm, ev_norm)
    return {"status": "success", "extracted_fields": merged}
