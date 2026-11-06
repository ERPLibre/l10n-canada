# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Canada - Tax Compliance Calendar",
    "summary": "Filing and payment deadlines of the CRA, Revenu Quebec, the "
    "Registraire des entreprises and the CNESST, with reminders",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "website": "https://github.com/OCA/l10n-canada",
    "author": "TechnoLibre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": [
        "account",
        "mail",
        "calendar_public_holiday",
        "l10n_ca_time_parameter",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/l10n_ca_tax_calendar_security.xml",
        "data/time_parameters.xml",
        "data/l10n_ca_tax_deadline_rule_data.xml",
        "data/mail_activity_type_data.xml",
        "data/ir_cron_data.xml",
        "views/l10n_ca_tax_deadline_views.xml",
        "views/l10n_ca_tax_deadline_rule_views.xml",
        "views/calendar_public_holiday_views.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
