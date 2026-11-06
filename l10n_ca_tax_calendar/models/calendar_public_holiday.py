# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

from odoo import api, models

from ..holidays import PUBLIC_HOLIDAYS, STATE_CODES


class CalendarPublicHoliday(models.Model):
    _inherit = "calendar.public.holiday"

    @api.model
    def _l10n_ca_load_holidays(self, holidays=None):
        """Create or complete the Canadian public holidays of each year.

        ``holidays`` maps a year to its lines, in the format of
        ``holidays.PUBLIC_HOLIDAYS`` (the default). The public holiday of a
        year and Canada is reused when it exists, since
        ``calendar_public_holiday`` allows one per year and country, and
        created otherwise. A shipped line already covered by a line of the
        same date (one for every province, or one sharing a province) is
        not duplicated: the covering lines get the jurisdiction of the
        shipped line and keep their name and provinces. Running it again
        changes nothing. Returns the created lines.
        """
        holidays = PUBLIC_HOLIDAYS if holidays is None else holidays
        canada = self.env.ref("base.ca")
        states = {
            key: self.env["res.country.state"].search(
                [("country_id", "=", canada.id), ("code", "in", codes)]
            )
            for key, codes in STATE_CODES.items()
        }
        no_states = self.env["res.country.state"]
        Line = self.env["calendar.public.holiday.line"]
        created = Line.browse()
        for year, lines in sorted(holidays.items()):
            holiday = self.search(
                [("year", "=", year), ("country_id", "=", canada.id)], limit=1
            )
            if not holiday:
                holiday = self.create({"year": year, "country_id": canada.id})
            values = []
            for month, day, name, variable, jurisdiction, state_key in lines:
                line_date = date(year, month, day)
                line_states = states[state_key] if state_key else no_states
                # An existing line covers the shipped one when it applies to
                # every province, or to one of its provinces.
                covering = holiday.line_ids.filtered(
                    lambda line, d=line_date, s=line_states: line.date == d
                    and (not line.state_ids or (s and line.state_ids & s))
                )
                if covering:
                    covering.write({"l10n_ca_jurisdiction": jurisdiction})
                    continue
                values.append(
                    {
                        "public_holiday_id": holiday.id,
                        "name": name,
                        "date": line_date,
                        "variable_date": variable,
                        "l10n_ca_jurisdiction": jurisdiction,
                        "state_ids": [(6, 0, line_states.ids)],
                    }
                )
            created |= Line.create(values)
        return created
