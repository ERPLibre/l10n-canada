# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Observations of one or more series, comma separated, as JSON. The Valet
# API documents it at https://www.bankofcanada.ca/valet/docs.
VALET_OBSERVATIONS_URL = "https://www.bankofcanada.ca/valet/observations/{series}/json"
VALET_TIMEOUT = 30

# Currencies of the FX_RATES_DAILY group: series FX<CUR>CAD gives the
# number of Canadian dollars for one unit of <CUR>, one observation per
# business day of the Bank of Canada. Weekends and bank holidays have no
# observation. The group lists its series at
# https://www.bankofcanada.ca/valet/groups/FX_RATES_DAILY/json
BOC_DAILY_CURRENCIES = [
    "AUD",
    "BRL",
    "CHF",
    "CNY",
    "EUR",
    "GBP",
    "HKD",
    "IDR",
    "INR",
    "JPY",
    "KRW",
    "MXN",
    "MYR",
    "NOK",
    "NZD",
    "PEN",
    "PLN",
    "RUB",
    "SAR",
    "SEK",
    "SGD",
    "THB",
    "TRY",
    "TWD",
    "USD",
    "VND",
    "ZAR",
]


def boc_series(currency):
    """Return the Valet series code of ``currency`` against the CAD."""
    return f"FX{currency}CAD"


class ResCurrencyRateProviderBOC(models.Model):
    _inherit = "res.currency.rate.provider"

    service = fields.Selection(
        selection_add=[("BOC", "Bank of Canada")],
        ondelete={"BOC": "set default"},
    )

    def _get_supported_currencies(self):
        self.ensure_one()
        if self.service != "BOC":
            return super()._get_supported_currencies()
        return ["CAD"] + BOC_DAILY_CURRENCIES

    def _obtain_rates(self, base_currency, currencies, date_from, date_to):
        """Return ``{iso_date: {currency: rate}}`` for the Valet observations.

        ``rate`` follows the Odoo convention: units of ``currency`` for one
        unit of ``base_currency`` (the company currency). The Bank of Canada
        quotes every currency in CAD, so for a base currency B and a currency
        X the rate is ``CAD per B / CAD per X``; the CAD itself is the series
        value of B. A day without observation for B or X (weekend, bank
        holiday, rate not yet published) yields no rate for that pair, and a
        day without any rate is left out of the result.
        """
        self.ensure_one()
        if self.service != "BOC":
            return super()._obtain_rates(base_currency, currencies, date_from, date_to)
        supported = set(self._get_supported_currencies())
        if base_currency not in supported:
            raise UserError(
                _(
                    "The Bank of Canada does not publish a rate for the "
                    "company currency %(currency)s.",
                    currency=base_currency,
                )
            )
        wanted = []
        for currency in currencies:
            if currency == base_currency or currency in wanted:
                continue
            if currency not in supported:
                _logger.warning(
                    "Bank of Canada: no daily rate for %s, currency skipped", currency
                )
                continue
            wanted.append(currency)
        if not wanted:
            return {}
        quoted = sorted({c for c in wanted + [base_currency] if c != "CAD"})
        observations = self._boc_fetch_observations(quoted, date_from, date_to)
        content = {}
        for day, cad_values in observations.items():
            cad_values = dict(cad_values, CAD=1.0)
            base_value = cad_values.get(base_currency)
            if not base_value:
                continue
            rates = {
                currency: base_value / cad_values[currency]
                for currency in wanted
                if cad_values.get(currency)
            }
            if rates:
                content[day] = rates
        return content

    def _boc_fetch_observations(self, currencies, date_from, date_to):
        """Return ``{iso_date: {currency: CAD per unit}}`` read from Valet.

        One request covers every currency and the whole date range, both
        bounds included. Empty or non-positive values are skipped. An HTTP
        error raises, which the caller ``_update`` turns into a message on
        the provider.
        """
        series = ",".join(boc_series(c) for c in currencies)
        response = requests.get(
            VALET_OBSERVATIONS_URL.format(series=series),
            params={
                "start_date": fields.Date.to_date(date_from).isoformat(),
                "end_date": fields.Date.to_date(date_to).isoformat(),
            },
            timeout=VALET_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        result = {}
        for observation in payload.get("observations") or []:
            day = observation.get("d")
            if not day:
                continue
            for currency in currencies:
                cell = observation.get(boc_series(currency)) or {}
                try:
                    value = float(cell.get("v") or 0.0)
                except (TypeError, ValueError):
                    continue
                if value > 0:
                    result.setdefault(day, {})[currency] = value
        return result
