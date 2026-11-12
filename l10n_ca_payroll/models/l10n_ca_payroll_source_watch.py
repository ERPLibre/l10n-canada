# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
import logging
import threading
from datetime import date

import requests

from odoo import _, api, fields, models

from ..tools.watch import WATCHERS, PageChanged

_logger = logging.getLogger(__name__)

# Order of gravity of the states: the worst one of the years checked wins.
STATE_ORDER = ("ok", "pending", "published", "differs", "error", "changed")
ATTENTION_STATES = ("published", "differs", "error", "changed")
# The client names itself as a robot with its project page. canada.ca leaves
# some free-form agent names unanswered until the timeout, while the
# "name/version (+URL)" form gets the page.
USER_AGENT = "l10n_ca_payroll/18.0 (+https://github.com/OCA/l10n-canada)"


class L10nCaPayrollSource(models.Model):
    """Weekly reading of the official pages behind the payroll figures.

    A source with a watcher (``watch_key``) is read for the current year and
    the next one. The figures found are compared with the time parameters
    in force on January 1 of that year; nothing is written to the
    parameters. A page that no longer has the structure the watcher reads,
    or that does not answer, is reported as such: it usually means the page
    moved or changed. Every state that needs a person schedules a to-do
    activity for a payroll manager, once per new finding.
    """

    _name = "l10n_ca.payroll.source"
    _inherit = ["l10n_ca.payroll.source", "mail.thread", "mail.activity.mixin"]

    watch_key = fields.Selection(
        selection="_selection_watch_key",
        string="Watcher",
        help="Reader of the official page that tells when the figures of a "
        "new year are published.",
    )
    watch_state = fields.Selection(
        [
            ("ok", "Up to date"),
            ("pending", "Next year not yet published"),
            ("published", "Published, not in the parameters"),
            ("differs", "Differs from the parameters"),
            ("error", "Page unreachable"),
            ("changed", "Page changed"),
        ],
        readonly=True,
        copy=False,
        tracking=True,
    )
    watch_date = fields.Datetime(string="Last Check", readonly=True, copy=False)
    watch_message = fields.Text(string="Check Result", readonly=True, copy=False)
    watch_digest = fields.Char(readonly=True, copy=False)
    watch_published_year = fields.Integer(
        string="Published Year",
        readonly=True,
        copy=False,
        help="Year whose publication the last check found, for a watcher that "
        "detects a publication without reading figures.",
    )
    watch_acknowledged_year = fields.Integer(
        string="Reviewed Year",
        copy=False,
        help="Last year whose publication a person has reviewed. A watcher "
        "that only detects a publication, without reading figures, stays up "
        "to date for that year.",
    )

    @api.model
    def _l10n_ca_watchers(self):
        """Return the watchers by key; provincial modules add theirs."""
        return dict(WATCHERS)

    @api.model
    def _selection_watch_key(self):
        return [(key, w.label) for key, w in self._l10n_ca_watchers().items()]

    @api.model
    def _l10n_ca_fetch(self, url, probe=False):
        """Return (HTTP status, content) of ``url``; content is None for a probe."""
        headers = {"User-Agent": USER_AGENT}
        if probe:
            response = requests.head(
                url, headers=headers, timeout=30, allow_redirects=True
            )
            return response.status_code, None
        response = requests.get(url, headers=headers, timeout=30)
        return response.status_code, response.content

    def _l10n_ca_parameter_value(self, code, year):
        """Return (value in force on January 1 of ``year``, its version year)."""
        Version = self.env["base.time.parameter.version"].sudo()
        version = Version.search(
            [
                ("parameter_id.code", "=", code),
                ("parameter_id.company_id", "=", False),
                ("date_from", "<=", date(year, 1, 1)),
            ],
            order="date_from desc",
            limit=1,
        )
        if not version:
            return None, None
        value = version.value
        if version.parameter_id.type in ("float", "integer"):
            value = float(value)
        elif isinstance(value, str):
            value = json.loads(value)
        return value, version.date_from.year

    @staticmethod
    def _l10n_ca_same(found, stored):
        """Return whether a figure read on a page matches the parameter.

        Brackets read on a page that lack the first one, from 0, match the
        stored brackets above 0.
        """
        if isinstance(found, list):
            if not isinstance(stored, list) or not found:
                return False
            found = [list(map(float, b)) for b in found]
            stored = [list(map(float, b)) for b in stored]
            if found[0][0] > 0:
                stored = [b for b in stored if b[0] > 0]
            return found == stored
        try:
            return abs(float(found) - float(stored)) < 1e-6
        except (TypeError, ValueError):
            return False

    def _l10n_ca_check_year(self, watcher, year, fetched):
        """Return (state, message, key) of one source for ``year``.

        ``fetched`` maps each URL already read in this run to its answer, so
        a page shared by the two years is read once. ``key`` describes the
        finding without words, so that a check run in another language is
        not taken for a new finding. A missing year is "pending" only after
        the current year: the year in force missing from its page means the
        page changed. Any error of the watcher on the content is a change of
        the page. A publication without figures is in force for the current
        year and for a year already reviewed, and needs a review for the
        next one.
        """
        url = watcher.url(year)
        probe = watcher.kind == "probe"
        if url not in fetched:
            try:
                fetched[url] = self._l10n_ca_fetch(url, probe=probe)
            except requests.RequestException as error:
                fetched[url] = error
        answer = fetched[url]
        if isinstance(answer, Exception):
            reason = type(answer).__name__
            message = _("%(year)s: %(url)s did not answer (%(error)s).") % {
                "year": year,
                "url": url,
                "error": reason,
            }
            return "error", message, [year, "error", reason]
        status, content = answer
        try:
            if probe:
                values = watcher.extract(status, year)
            elif status in (404, 410) and watcher.kind == "yearly":
                values = None
            elif status != 200:
                raise PageChanged(f"HTTP {status}")
            else:
                values = watcher.extract(content, year)
            current = fields.Date.context_today(self).year
            if values is None and year <= current:
                raise PageChanged(f"no figures for {year}, the year in force")
        except Exception as error:  # noqa: BLE001 - any failure means the page changed
            reason = str(error) if isinstance(error, PageChanged) else repr(error)
            message = _(
                "%(year)s: %(url)s no longer has the expected content (%(error)s): "
                "the page moved or changed, check it and the watcher."
            ) % {"year": year, "url": url, "error": reason}
            return "changed", message, [year, "changed", reason]
        if values is None:
            message = _("%(year)s: not yet published.") % {"year": year}
            return "pending", message, [year, "pending"]
        if not values:
            if year <= max(current, self.watch_acknowledged_year):
                message = _("%(year)s: published, in force.") % {"year": year}
                return "ok", message, [year, "ok"]
            message = _(
                "%(year)s: published at %(url)s; update the parameters it sets, "
                "then mark the year as reviewed."
            ) % {"year": year, "url": url}
            return "published", message, [year, "published"]
        lines, states, key = [], [], [year]
        for code, value in values.items():
            stored, version_year = self._l10n_ca_parameter_value(code, year)
            if stored is not None and self._l10n_ca_same(value, stored):
                states.append("ok")
                lines.append(
                    _("%(code)s = %(value)s: matches.") % {"code": code, "value": value}
                )
            elif version_year == year:
                states.append("differs")
                lines.append(
                    _(
                        "%(code)s: the page gives %(value)s, the %(year)s version "
                        "holds %(stored)s."
                    )
                    % {"code": code, "value": value, "year": year, "stored": stored}
                )
            else:
                states.append("published")
                lines.append(
                    _("%(code)s: %(value)s published for %(year)s, no version yet.")
                    % {"code": code, "value": value, "year": year}
                )
            key.append([code, value, states[-1]])
        state = max(states, key=STATE_ORDER.index) if states else "ok"
        return state, "\n".join([f"{year}:"] + lines), [state] + key

    def action_l10n_ca_watch(self):
        """Read the page of each source for the current and the next year."""
        today = fields.Date.context_today(self)
        fetched = {}
        for source in self.filtered("watch_key"):
            watcher = source._l10n_ca_watchers().get(source.watch_key)
            if not watcher:
                continue
            years = (today.year, today.year + 1)
            results = [source._l10n_ca_check_year(watcher, y, fetched) for y in years]
            state = max((r[0] for r in results), key=STATE_ORDER.index)
            digest = json.dumps([r[2] for r in results], sort_keys=True)
            published = [
                year
                for year, result in zip(years, results, strict=True)
                if result[2] == [year, "published"]
            ]
            changed = (state, digest) != (source.watch_state, source.watch_digest)
            source.write(
                {
                    "watch_state": state,
                    "watch_message": "\n".join(r[1] for r in results),
                    "watch_digest": digest,
                    "watch_published_year": max(published) if published else 0,
                    "watch_date": fields.Datetime.now(),
                }
            )
            if changed and state in ATTENTION_STATES:
                source._l10n_ca_watch_notify()
        return True

    def action_l10n_ca_watch_acknowledge(self):
        """Mark the published year as reviewed and close the open to-dos."""
        for source in self.filtered("watch_published_year"):
            source.watch_acknowledged_year = source.watch_published_year
        self.activity_feedback(["mail.mail_activity_data_todo"])
        return self.action_l10n_ca_watch()

    def _l10n_ca_watch_notify(self):
        """Post the result and schedule one open to-do for a payroll manager."""
        self.ensure_one()
        self.message_post(body=self.watch_message)
        if self.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref("mail.mail_activity_data_todo")
        ):
            return
        managers = self.env.ref("payroll.group_payroll_manager").users.filtered(
            lambda u: u.active and not u.share
        )
        if not managers:
            return
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=managers.sorted("id")[:1].id,
            summary=_("Official payroll source: %(state)s")
            % {
                "state": dict(
                    self._fields["watch_state"]._description_selection(self.env)
                )[self.watch_state],
            },
            note=self.watch_message,
        )

    @api.model
    def _cron_l10n_ca_watch(self):
        """Weekly check of every watched source; one failure does not stop it.

        Each source is committed once checked, so a worker stopped by its
        time limit keeps the sources already done.
        """
        for source in self.search([("watch_key", "!=", False)]):
            try:
                with self.env.cr.savepoint():
                    source.action_l10n_ca_watch()
            except Exception:
                _logger.exception("Official source watch failed for %s", source.name)
            if not getattr(threading.current_thread(), "testing", False):
                self.env.cr.commit()  # pylint: disable=invalid-commit
