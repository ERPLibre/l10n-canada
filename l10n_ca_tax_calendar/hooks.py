# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def post_init_hook(env):
    """Load the Canadian public holidays, reusing those already present.

    A plain XML record would fail the install when the database already
    holds a public holiday for Canada and one of the shipped years.
    """
    env["calendar.public.holiday"]._l10n_ca_load_holidays()
