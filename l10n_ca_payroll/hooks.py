# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def post_init_hook(env):
    """Set up the Canadian payroll of every Canadian company.

    Each company gets the "Canada - Base" structure as its default salary
    structure and, when its chart of accounts is ``ca_2023``, the proposed
    accounts on the statutory salary rules. Accounts already set are kept.
    """
    companies = env["res.company"].search([("partner_id.country_id.code", "=", "CA")])
    for company in companies:
        company.l10n_ca_payroll_setup()
