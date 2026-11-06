# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Canada - Quebec Payroll",
    "summary": "Quebec payroll: QPP, QPIP, Quebec income tax per TP-1015.F, "
    "HSF, CNT, CNESST and WSDRF, RL-1 slips and Revenu Quebec remittances",
    "version": "18.0.1.0.0",
    "category": "Payroll/Localizations",
    "website": "https://github.com/OCA/l10n-canada",
    "author": "TechnoLibre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": ["l10n_ca_payroll"],
    "data": [
        "security/l10n_ca_qc_payroll_security.xml",
        "security/ir.model.access.csv",
        "data/time_parameters.xml",
        "data/hr_payroll_data.xml",
        "views/hr_contract_views.xml",
        "views/l10n_ca_payroll_t4_views.xml",
        "views/l10n_ca_qc_remittance_views.xml",
        "views/l10n_ca_qc_rl1_views.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
