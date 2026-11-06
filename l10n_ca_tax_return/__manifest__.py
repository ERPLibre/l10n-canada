# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Canada - GST/HST and QST Returns",
    "summary": "Compute, close and print the GST/HST (GST34) and the "
    "Quebec FPZ-500 returns from the l10n_ca tax report definitions",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "website": "https://github.com/OCA/l10n-canada",
    "author": "TechnoLibre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": [
        "l10n_ca",
        "l10n_ca_time_parameter",
        "date_range",
        "report_xlsx",
    ],
    "data": [
        "security/l10n_ca_tax_return_security.xml",
        "security/ir.model.access.csv",
        "data/time_parameters.xml",
        "report/tax_return_report.xml",
        "views/l10n_ca_tax_return_views.xml",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
        "wizards/l10n_ca_bad_debt_wizard_views.xml",
        "views/menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
