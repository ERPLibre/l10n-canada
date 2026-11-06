# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Canada - GIFI",
    "summary": "General Index of Financial Information (GIFI) codes, "
    "account mapping and T2 schedules 100, 101 and 125",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "website": "https://github.com/OCA/l10n-canada",
    "author": "TechnoLibre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": [
        "account",
        "l10n_ca",
        "l10n_ca_time_parameter",
        "date_range",
        "report_xlsx",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/l10n_ca_gifi_security.xml",
        "data/l10n.ca.gifi.code.csv",
        "data/l10n.ca.gifi.code-relations.csv",
        "data/l10n_ca_gifi_account_type_map_data.xml",
        "data/time_parameters.xml",
        "views/l10n_ca_gifi_code_views.xml",
        "views/l10n_ca_gifi_account_type_map_views.xml",
        "views/account_account_views.xml",
        "views/l10n_ca_gifi_statement_views.xml",
        "views/res_config_settings_views.xml",
        "report/l10n_ca_gifi_reports.xml",
        "report/l10n_ca_gifi_statement_templates.xml",
        "views/menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
