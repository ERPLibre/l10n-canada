# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def post_init_hook(env):
    """Add the Northwest Territories salary rules to the Canadian payroll.

    Runs the Canadian payroll set-up again, which this module extends: every
    "Canada - Base" structure receives the Northwest Territories rules and,
    with the ``ca_2023`` chart, the rules receive their accounts. Accounts
    already set are kept.
    """
    companies = env["res.company"].search([("partner_id.country_id.code", "=", "CA")])
    companies.l10n_ca_payroll_setup()
