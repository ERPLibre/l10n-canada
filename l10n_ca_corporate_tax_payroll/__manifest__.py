# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Canada - Quebec SBD Remunerated Hours from Payroll",
    "summary": "Count the hours of the done payslips in the remunerated "
    "hours of the Quebec small business deduction",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "website": "https://github.com/OCA/l10n-canada",
    "author": "TechnoLibre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": ["l10n_ca_corporate_tax", "l10n_ca_qc_payroll"],
    "data": [
        "views/hr_employee_views.xml",
        "views/l10n_ca_paid_hours_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
