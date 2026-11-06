# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Canada - Time Parameters",
    "summary": "Dated fiscal parameters and company tax profile "
    "shared by the Canadian localization modules",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "website": "https://github.com/OCA/l10n-canada",
    "author": "TechnoLibre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": ["account", "base_time_parameter"],
    "data": [
        "security/l10n_ca_time_parameter_security.xml",
        "views/base_time_parameter_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
}
