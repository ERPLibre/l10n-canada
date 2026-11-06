# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Canada - Owner-Manager Corporate Tax",
    "summary": "Shareholder loans, Quebec paid-hours rule, corporate tax "
    "estimate, dividends with T5 and RL-3 slips for a Quebec CCPC",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "website": "https://github.com/OCA/l10n-canada",
    "author": "TechnoLibre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": ["account", "mail", "l10n_ca", "l10n_ca_time_parameter", "report_xlsx"],
    "data": [
        "security/l10n_ca_corporate_tax_security.xml",
        "security/ir.model.access.csv",
        "data/time_parameters.xml",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/menus.xml",
        "views/account_account_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
        "views/l10n_ca_shareholder_loan_views.xml",
        "views/l10n_ca_paid_hours_views.xml",
        "views/l10n_ca_corporate_tax_estimate_views.xml",
        "views/l10n_ca_dividend_views.xml",
        "views/l10n_ca_dividend_slip_views.xml",
        "wizards/l10n_ca_shareholder_loan_wizard_views.xml",
        "wizards/l10n_ca_dividend_slip_wizard_views.xml",
        "report/l10n_ca_dividend_slip_xlsx.xml",
    ],
    "installable": True,
}
