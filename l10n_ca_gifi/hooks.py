# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def post_init_hook(env):
    """Assign the GIFI codes of the ca_2023 chart to the existing companies.

    Companies created after the installation receive them from the chart
    template; an account that already has a code keeps it.
    """
    companies = env["res.company"].search([("chart_template", "=", "ca_2023")])
    companies._l10n_ca_gifi_assign_default_codes()
