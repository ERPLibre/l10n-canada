# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Canada - Capital Cost Allowance",
    "summary": "Tax depreciation (CCA, T2 Schedule 8) next to the book "
    "depreciation of the assets, with book to tax reconciliation",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "website": "https://github.com/OCA/l10n-canada",
    "author": "TechnoLibre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "depends": ["account_asset_management", "l10n_ca_time_parameter"],
    "data": [
        "security/ir.model.access.csv",
        "security/l10n_ca_cca_security.xml",
        "data/time_parameters.xml",
        "data/l10n_ca_cca_class_data.xml",
        "views/l10n_ca_cca_class_views.xml",
        "views/l10n_ca_cca_schedule_views.xml",
        "views/account_asset_profile_views.xml",
        "views/account_asset_views.xml",
        "views/menus.xml",
        "report/l10n_ca_cca_schedule_report.xml",
    ],
    "installable": True,
}
