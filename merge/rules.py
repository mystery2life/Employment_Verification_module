"""
merge.rules
-----------
Canonical field list, source priority, and source→canonical key maps.

- Canonical fields are what the unified JSON will expose.
- PRIORITY expresses hard preference (paystub wins where applicable).
- *_FIELD_MAP translate raw extractor keys into canonical names.
"""

# Final fields expected in the unified JSON
CANONICAL_FIELDS = [
    "EmployeeName",
    "EmployerName",
    "EmployerAddress",
    "EIN",
    "HireDate",
    "JobTitle",
    "PayDate",
    "GrossAmount",
    "TotalHours",
    "PayPeriodStartDate",
    "PayPeriodEndDate",
    "PayFrequency",
    "LossOfEmploymentDate",
    "LossOfEmploymentReason",
    "DateOfLastPaycheck",
]

# Hard priority by field (no confidence-based arbitration)
PRIORITY = {
    # Shared (paystub first)
    "EmployeeName": ["paystub", "ev"],
    "EmployerName": ["paystub", "ev"],
    "EmployerAddress": ["paystub", "ev"],
    "EIN": ["paystub", "ev"],
    "JobTitle": ["paystub", "ev"],
    "TotalHours": ["paystub", "ev"],

    # Paystub-only
    "PayDate": ["paystub"],
    "GrossAmount": ["paystub"],                # from CurrentPeriodGrossPay
    "PayPeriodStartDate": ["paystub"],
    "PayPeriodEndDate": ["paystub"],
    "PayFrequency": ["derived"],               # computed from paystub dates

    # EV-only
    "HireDate": ["ev"],
    "LossOfEmploymentDate": ["ev"],
    "LossOfEmploymentReason": ["ev"],
    "DateOfLastPaycheck": ["ev"],
}

# Map raw paystub keys to canonical names
PAYSTUB_FIELD_MAP = {
    "EmployeeName": "EmployeeName",
    "EmployerName": "EmployerName",
    "EmployerAddress": "EmployerAddress",
    "EIN": "EIN",                              # only if your stub has it
    "JobTitle": "JobTitle",
    "PayDate": "PayDate",
    "CurrentPeriodGrossPay": "GrossAmount",
    "PayPeriodStartDate": "PayPeriodStartDate",
    "PayPeriodEndDate": "PayPeriodEndDate",
    "TotalHoursWorked": "TotalHours",

    # explicitly ignored (present but not in canonical)
    "AveragePayRate": None,
    "YearToDateGrossPay": None,
}

# Map raw EV keys to canonical names (mirrors your custom extractor)
EV_FIELD_MAP = {
    "EmployeeName": "EmployeeName",
    "CompanyName": "EmployerName",
    "Company Address": "EmployerAddress",
    "EIN": "EIN",
    "HireDate": "HireDate",
    "JobTitle": "JobTitle",
    "AverageWorkingHours": "TotalHours",          # EV fallback only

    "EmplyomentEndDate": "LossOfEmploymentDate",
    "EmploymentEndDateReason": "LossOfEmploymentReason",
    "FinalPayCheckDate": "DateOfLastPaycheck",

    # present but not part of the final schema
    "FirstPayCheckDate": None,
    "PayFrequency": None,                         # must be derived from stub
    "AvgPay": None,
    "AvgPayFrequency": None,
    "EmplymentType": None,
    "FinalPayCheckAmt": None,
    "FinalFourPayCheckTable": None,
}
