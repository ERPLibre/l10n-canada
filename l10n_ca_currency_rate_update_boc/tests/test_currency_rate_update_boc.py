# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date
from unittest import mock

import requests

from odoo.tests import TransactionCase, tagged

_REQUESTS_GET = (
    "odoo.addons.l10n_ca_currency_rate_update_boc.models."
    "res_currency_rate_provider_boc.requests.get"
)

# Valet answer for FXEURCAD,FXUSDCAD from Friday 2026-10-09 to Tuesday
# 2026-10-13, values invented. Saturday, Sunday and the Monday holiday
# have no observation, as in the real API.
VALET_PAYLOAD = {
    "terms": {"url": "https://www.bankofcanada.ca/terms/"},
    "seriesDetail": {
        "FXEURCAD": {"label": "EUR/CAD"},
        "FXUSDCAD": {"label": "USD/CAD"},
    },
    "observations": [
        {"d": "2026-10-09", "FXEURCAD": {"v": "1.6000"}, "FXUSDCAD": {"v": "1.4000"}},
        {"d": "2026-10-13", "FXEURCAD": {"v": "1.5000"}, "FXUSDCAD": {"v": "1.2500"}},
    ],
}


def _response(payload=None, error=None):
    response = mock.MagicMock()
    response.json.return_value = payload
    if error:
        response.raise_for_status.side_effect = error
    return response


@tagged("post_install", "-at_install")
class TestCurrencyRateUpdateBOC(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Assertions read the English messages whatever languages the
        # database has loaded.
        cls.env = cls.env(context=dict(cls.env.context, lang="en_US"))
        cls.cad = cls.env.ref("base.CAD")
        cls.usd = cls.env.ref("base.USD")
        cls.eur = cls.env.ref("base.EUR")
        (cls.cad | cls.usd | cls.eur).write({"active": True})
        cls.Rate = cls.env["res.currency.rate"]
        cls.company_cad = cls.env["res.company"].create(
            {"name": "BOC test CAD", "currency_id": cls.cad.id}
        )
        cls.company_eur = cls.env["res.company"].create(
            {"name": "BOC test EUR", "currency_id": cls.eur.id}
        )
        cls.Provider = cls.env["res.currency.rate.provider"]
        cls.provider_cad = cls.Provider.create(
            {
                "service": "BOC",
                "company_id": cls.company_cad.id,
                "currency_ids": [(6, 0, (cls.usd | cls.eur).ids)],
            }
        )
        cls.provider_eur = cls.Provider.create(
            {
                "service": "BOC",
                "company_id": cls.company_eur.id,
                "currency_ids": [(6, 0, (cls.usd | cls.cad).ids)],
            }
        )

    def _rate(self, company, currency, day):
        return self.Rate.search(
            [
                ("company_id", "=", company.id),
                ("currency_id", "=", currency.id),
                ("name", "=", day),
            ]
        )

    def test_supported_currencies(self):
        supported = self.provider_cad._get_supported_currencies()
        self.assertIn("CAD", supported)
        self.assertIn("USD", supported)
        self.assertIn("EUR", supported)
        self.assertEqual(len(supported), len(set(supported)))
        self.assertIn(self.usd, self.provider_cad.available_currency_ids)

    def test_request_shape(self):
        with mock.patch(_REQUESTS_GET, return_value=_response(VALET_PAYLOAD)) as get:
            self.provider_cad._update(date(2026, 10, 9), date(2026, 10, 13))
        url = get.call_args.args[0]
        self.assertTrue(url.endswith("/valet/observations/FXEURCAD,FXUSDCAD/json"))
        self.assertEqual(
            get.call_args.kwargs["params"],
            {"start_date": "2026-10-09", "end_date": "2026-10-13"},
        )
        self.assertTrue(get.call_args.kwargs["timeout"])

    def test_cad_company_rates(self):
        """Odoo rate = units of currency per CAD = 1 / (CAD per unit).

        USD on 2026-10-09: 1 / 1.40 = 0.714285...; EUR: 1 / 1.60 = 0.625.
        """
        with mock.patch(_REQUESTS_GET, return_value=_response(VALET_PAYLOAD)):
            self.provider_cad._update(date(2026, 10, 9), date(2026, 10, 13))
        usd_friday = self._rate(self.company_cad, self.usd, date(2026, 10, 9))
        self.assertAlmostEqual(usd_friday.rate, 1 / 1.40, places=9)
        self.assertEqual(usd_friday.provider_id, self.provider_cad)
        eur_friday = self._rate(self.company_cad, self.eur, date(2026, 10, 9))
        self.assertAlmostEqual(eur_friday.rate, 0.625, places=9)
        usd_tuesday = self._rate(self.company_cad, self.usd, date(2026, 10, 13))
        self.assertAlmostEqual(usd_tuesday.rate, 0.8, places=9)

    def test_no_rate_on_days_without_observation(self):
        with mock.patch(_REQUESTS_GET, return_value=_response(VALET_PAYLOAD)):
            self.provider_cad._update(date(2026, 10, 9), date(2026, 10, 13))
        for day in (date(2026, 10, 10), date(2026, 10, 11), date(2026, 10, 12)):
            self.assertFalse(self._rate(self.company_cad, self.usd, day))
        self.assertEqual(
            len(self.Rate.search([("company_id", "=", self.company_cad.id)])), 4
        )

    def test_cross_rates_for_eur_company(self):
        """Base EUR: USD per EUR = 1.60 / 1.40 = 1.142857...; CAD per EUR = 1.60.

        Tuesday: USD per EUR = 1.50 / 1.25 = 1.2; CAD per EUR = 1.50.
        """
        with mock.patch(_REQUESTS_GET, return_value=_response(VALET_PAYLOAD)) as get:
            self.provider_eur._update(date(2026, 10, 9), date(2026, 10, 13))
        self.assertIn("FXEURCAD,FXUSDCAD", get.call_args.args[0])
        friday = date(2026, 10, 9)
        self.assertAlmostEqual(
            self._rate(self.company_eur, self.usd, friday).rate, 1.60 / 1.40, places=9
        )
        self.assertAlmostEqual(
            self._rate(self.company_eur, self.cad, friday).rate, 1.60, places=9
        )
        tuesday = date(2026, 10, 13)
        self.assertAlmostEqual(
            self._rate(self.company_eur, self.usd, tuesday).rate, 1.2, places=9
        )
        self.assertAlmostEqual(
            self._rate(self.company_eur, self.cad, tuesday).rate, 1.5, places=9
        )

    def test_missing_base_observation_skips_day(self):
        payload = {
            "observations": [
                {"d": "2026-10-09", "FXUSDCAD": {"v": "1.4000"}},
                {"d": "2026-10-13", "FXEURCAD": {"v": ""}, "FXUSDCAD": {"v": "1.25"}},
            ]
        }
        with mock.patch(_REQUESTS_GET, return_value=_response(payload)):
            rates = self.provider_eur._obtain_rates(
                "EUR", ["USD", "CAD"], date(2026, 10, 9), date(2026, 10, 13)
            )
        self.assertEqual(rates, {})

    def test_newest_only(self):
        with mock.patch(_REQUESTS_GET, return_value=_response(VALET_PAYLOAD)):
            self.provider_cad._update(
                date(2026, 10, 9), date(2026, 10, 13), newest_only=True
            )
        self.assertFalse(self._rate(self.company_cad, self.usd, date(2026, 10, 9)))
        self.assertTrue(self._rate(self.company_cad, self.usd, date(2026, 10, 13)))

    def test_empty_range(self):
        payload = {"observations": []}
        with mock.patch(_REQUESTS_GET, return_value=_response(payload)):
            self.provider_cad._update(date(2026, 10, 10), date(2026, 10, 11))
        self.assertFalse(self.Rate.search([("company_id", "=", self.company_cad.id)]))

    def test_http_error_posts_message(self):
        error = requests.HTTPError("404 Client Error")
        messages_before = len(self.provider_cad.message_ids)
        with mock.patch(_REQUESTS_GET, return_value=_response(error=error)):
            self.provider_cad._update(date(2026, 10, 9), date(2026, 10, 13))
        self.assertFalse(self.Rate.search([("company_id", "=", self.company_cad.id)]))
        self.assertGreater(len(self.provider_cad.message_ids), messages_before)
        self.assertIn("404", self.provider_cad.message_ids[0].body)

    def test_unsupported_currency_is_skipped(self):
        ars = self.env.ref("base.ARS")
        with mock.patch(_REQUESTS_GET, return_value=_response(VALET_PAYLOAD)) as get:
            rates = self.provider_cad._obtain_rates(
                "CAD", ["USD", ars.name, "CAD"], date(2026, 10, 9), date(2026, 10, 9)
            )
        self.assertIn("/FXUSDCAD/", get.call_args.args[0])
        self.assertEqual(set(rates["2026-10-09"]), {"USD"})

    def test_unsupported_company_currency(self):
        company = self.env["res.company"].create(
            {"name": "BOC test ARS", "currency_id": self.env.ref("base.ARS").id}
        )
        provider = self.Provider.create(
            {
                "service": "BOC",
                "company_id": company.id,
                "currency_ids": [(6, 0, self.usd.ids)],
            }
        )
        with mock.patch(_REQUESTS_GET) as get:
            provider._update(date(2026, 10, 9), date(2026, 10, 13))
        get.assert_not_called()
        self.assertIn("ARS", provider.message_ids[0].body)
