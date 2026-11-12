# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Canada - Northwest Territories Payroll",
    "summary": "Northwest Territories payroll: territorial income tax per T4127, "
    "payroll tax withheld from the employees and WSCC assessments",
    "version": "18.0.1.0.0",
    "category": "Payroll/Localizations",
    "website": "https://github.com/OCA/l10n-canada",
    "author": "TechnoLibre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": ["l10n_ca_payroll"],
    "data": [
        "data/time_parameters.xml",
        "data/hr_payroll_data.xml",
        "data/l10n_ca_payroll_source_data.xml",
        "views/hr_contract_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
