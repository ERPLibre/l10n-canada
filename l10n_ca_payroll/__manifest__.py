# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Canada - Payroll",
    "summary": "Canadian federal payroll: CPP, CPP2, EI and federal income "
    "tax per T4127, T4 slips and PD7A remittances",
    "version": "18.0.1.0.0",
    "category": "Payroll/Localizations",
    "website": "https://github.com/OCA/l10n-canada",
    "author": "TechnoLibre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": [
        "hr_contract",
        "payroll",
        "payroll_account",
        "payroll_rule_time_parameter",
        "l10n_ca_time_parameter",
    ],
    "data": [
        "security/l10n_ca_payroll_security.xml",
        "security/ir.model.access.csv",
        "data/time_parameters.xml",
        "data/hr_payroll_data.xml",
        "data/l10n_ca_payroll_source_data.xml",
        "data/ir_cron_data.xml",
        "views/hr_contract_views.xml",
        "views/hr_payslip_views.xml",
        "views/l10n_ca_payroll_remittance_views.xml",
        "views/l10n_ca_payroll_t4_views.xml",
        "views/res_config_settings_views.xml",
        "views/l10n_ca_payroll_source_views.xml",
        "views/l10n_ca_payroll_source_watch_views.xml",
        "views/menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
