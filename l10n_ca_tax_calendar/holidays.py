# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Canadian public holidays that move the tax deadlines, by year.

Each line is ``(month, day, name, variable_date, jurisdiction, states)``:

- ``jurisdiction`` is a value of ``calendar.public.holiday.line.
  l10n_ca_jurisdiction``. ``federal`` and ``both`` follow the list of
  public holidays of the CRA; ``quebec`` and ``both`` follow the
  Interpretation Act of Quebec, s. 61(23); ``quebec_payroll`` marks a day
  the offices of Revenu Quebec are closed, which the source deduction
  guide (TP-1015.G) does not count as a business day.
- ``states`` is ``qc`` (Quebec only), ``not_qc`` (every province and
  territory but Quebec) or ``None`` (everywhere).

The closure days of Revenu Quebec follow the office closure list of the
Quebec public service: December 24, 25, 26 and 31, January 1 and 2, a day
falling on a weekend being moved by that list. A move that list has not
yet published is left out: a missing holiday shows a deadline earlier,
never later. December 26 on a weekday is ``both``: the CRA lists it and
Revenu Quebec is closed; on a weekend it is ``federal`` and the moved
closure day is a separate ``quebec_payroll`` line.

Sources: https://www.canada.ca/en/revenue-agency/services/tax/public-holidays.html
https://www.legisquebec.gouv.qc.ca/en/document/cs/I-16
https://www.revenuquebec.ca/en/contact-us/holidays/
"""

PUBLIC_HOLIDAYS = {
    2025: [
        (1, 1, "New Year's Day", False, "both", None),
        (
            1,
            2,
            "Day after New Year's Day (Revenu Quebec closed)",
            False,
            "quebec_payroll",
            None,
        ),
        (4, 18, "Good Friday", True, "both", None),
        (4, 21, "Easter Monday", True, "both", None),
        (5, 19, "Victoria Day / National Patriots' Day", True, "both", None),
        (6, 24, "Saint-Jean-Baptiste Day", False, "both", "qc"),
        (7, 1, "Canada Day", False, "both", None),
        (8, 4, "Civic Holiday", True, "federal", "not_qc"),
        (9, 1, "Labour Day", True, "both", None),
        (9, 30, "National Day for Truth and Reconciliation", False, "federal", None),
        (10, 13, "Thanksgiving Day", True, "both", None),
        (11, 11, "Remembrance Day", False, "federal", None),
        (12, 24, "Christmas Eve (Revenu Quebec closed)", False, "quebec_payroll", None),
        (12, 25, "Christmas Day", False, "both", None),
        (12, 26, "Boxing Day (Revenu Quebec closed)", False, "both", None),
        (
            12,
            31,
            "New Year's Eve (Revenu Quebec closed)",
            False,
            "quebec_payroll",
            None,
        ),
    ],
    2026: [
        (1, 1, "New Year's Day", False, "both", None),
        (
            1,
            2,
            "Day after New Year's Day (Revenu Quebec closed)",
            False,
            "quebec_payroll",
            None,
        ),
        (4, 3, "Good Friday", True, "both", None),
        (4, 6, "Easter Monday", True, "both", None),
        (5, 18, "Victoria Day / National Patriots' Day", True, "both", None),
        (6, 24, "Saint-Jean-Baptiste Day", False, "both", "qc"),
        (7, 1, "Canada Day", False, "both", None),
        (8, 3, "Civic Holiday", True, "federal", "not_qc"),
        (9, 7, "Labour Day", True, "both", None),
        (9, 30, "National Day for Truth and Reconciliation", False, "federal", None),
        (10, 12, "Thanksgiving Day", True, "both", None),
        (11, 11, "Remembrance Day", False, "federal", None),
        (12, 24, "Christmas Eve (Revenu Quebec closed)", False, "quebec_payroll", None),
        (12, 25, "Christmas Day", False, "both", None),
        (12, 26, "Boxing Day", False, "federal", None),
        (
            12,
            28,
            "Boxing Day, moved (Revenu Quebec closed)",
            True,
            "quebec_payroll",
            None,
        ),
        (
            12,
            31,
            "New Year's Eve (Revenu Quebec closed)",
            False,
            "quebec_payroll",
            None,
        ),
    ],
    2027: [
        (1, 1, "New Year's Day", False, "both", None),
        (
            1,
            4,
            "Day after New Year's Day, moved (Revenu Quebec closed)",
            True,
            "quebec_payroll",
            None,
        ),
        (3, 26, "Good Friday", True, "both", None),
        (3, 29, "Easter Monday", True, "both", None),
        (5, 24, "Victoria Day / National Patriots' Day", True, "both", None),
        (6, 24, "Saint-Jean-Baptiste Day", False, "both", "qc"),
        (7, 1, "Canada Day", False, "both", None),
        (8, 2, "Civic Holiday", True, "federal", "not_qc"),
        (9, 6, "Labour Day", True, "both", None),
        (9, 30, "National Day for Truth and Reconciliation", False, "federal", None),
        (10, 11, "Thanksgiving Day", True, "both", None),
        (11, 11, "Remembrance Day", False, "federal", None),
        (12, 24, "Christmas Eve (Revenu Quebec closed)", False, "quebec_payroll", None),
        (12, 25, "Christmas Day", False, "both", None),
        (12, 26, "Boxing Day", False, "federal", None),
        (
            12,
            31,
            "New Year's Eve (Revenu Quebec closed)",
            False,
            "quebec_payroll",
            None,
        ),
    ],
}

# Province codes of ``res.country.state`` for the ``states`` column.
PROVINCES_NOT_QC = [
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NS",
    "NT",
    "NU",
    "ON",
    "PE",
    "SK",
    "YT",
]
STATE_CODES = {"qc": ["QC"], "not_qc": PROVINCES_NOT_QC}
