# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

# Periods are looked up this far before the start of the horizon, so a
# deadline due in the horizon is found when its offset from the period end
# is at most this long. The longest offset of a shipped rule is six months
# (income tax returns). The timing parameters must cover the periods this
# reaches back to.
LOOKBACK_MONTHS = 12


class L10nCaTaxDeadline(models.Model):
    _name = "l10n.ca.tax.deadline"
    _description = "Canadian Tax Deadline"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "due_date, sequence, id"
    _check_company_auto = True

    # Not stored: the rule name is translated, and a stored name would keep
    # the language of the user or the scheduled action that created it.
    name = fields.Char(compute="_compute_name", search="_search_name")
    rule_id = fields.Many2one(
        "l10n.ca.tax.deadline.rule",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(related="rule_id.sequence", store=True)
    rule_description = fields.Text(related="rule_id.description")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    authority = fields.Selection(related="rule_id.authority", store=True)
    category = fields.Selection(related="rule_id.category", store=True)
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    due_date = fields.Date(required=True, tracking=True, index=True)
    state = fields.Selection(
        [("todo", "To Do"), ("done", "Done"), ("cancel", "Cancelled")],
        default="todo",
        required=True,
        tracking=True,
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        tracking=True,
        domain="[('share', '=', False)]",
    )
    done_date = fields.Date()
    reference = fields.Char(
        help="Confirmation number of the filing or the payment.",
    )
    reminder_activity_id = fields.Many2one(
        "mail.activity", readonly=True, ondelete="set null", copy=False
    )
    reminder_sent = fields.Boolean(readonly=True, copy=False)
    is_overdue = fields.Boolean(
        compute="_compute_is_overdue", search="_search_is_overdue"
    )
    days_left = fields.Integer(compute="_compute_is_overdue")
    color = fields.Integer(compute="_compute_is_overdue")

    _sql_constraints = [
        (
            "rule_company_period_uniq",
            "UNIQUE(rule_id, company_id, period_end)",
            "A rule has one deadline per company and period.",
        ),
    ]

    @api.depends("rule_id.name", "period_start", "period_end")
    @api.depends_context("lang")
    def _compute_name(self):
        for deadline in self:
            if (
                deadline.period_start == deadline.period_end
                or not deadline.period_start
            ):
                period = fields.Date.to_string(deadline.period_end)
            else:
                period = _(
                    "%(start)s to %(end)s",
                    start=fields.Date.to_string(deadline.period_start),
                    end=fields.Date.to_string(deadline.period_end),
                )
            deadline.name = f"{deadline.rule_id.name or ''} ({period})"

    def _search_name(self, operator, value):
        """Search the name on the rule name, in the language of the user."""
        return [("rule_id.name", operator, value)]

    @api.depends("due_date", "state")
    @api.depends_context("tz")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for deadline in self:
            deadline.days_left = (
                (deadline.due_date - today).days if deadline.due_date else 0
            )
            deadline.is_overdue = deadline.state == "todo" and deadline.days_left < 0
            if deadline.state != "todo":
                deadline.color = 0
            elif deadline.is_overdue:
                deadline.color = 1
            elif deadline.days_left <= 7:
                deadline.color = 2
            else:
                deadline.color = 10

    def _search_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        overdue = [("state", "=", "todo"), ("due_date", "<", today)]
        if (operator == "=") == bool(value):
            return overdue
        return ["!", "&", *overdue]

    def _l10n_ca_mark_done(self):
        self.write({"state": "done", "done_date": fields.Date.context_today(self)})

    def action_done(self):
        todo = self.filtered(lambda d: d.state == "todo")
        reminders = todo.reminder_activity_id
        todo._l10n_ca_mark_done()
        # Closing the reminder keeps the chatter trace; the hook on
        # mail.activity skips deadlines already done.
        reminders.exists().action_feedback(feedback=_("Deadline marked as done."))
        return True

    def action_cancel(self):
        self.reminder_activity_id.exists().unlink()
        self.write({"state": "cancel"})
        return True

    def action_reset_todo(self):
        self.write({"state": "todo", "done_date": False})
        return True

    @api.model
    def _cron_generate(self):
        """Scheduled action: deadlines of every Canadian company, then reminders."""
        companies = self.env["res.company"].search(
            [("partner_id.country_id.code", "=", "CA")]
        )
        self._l10n_ca_generate(companies)
        self._l10n_ca_schedule_reminders()

    @api.model
    def _l10n_ca_generate(self, companies, date_from=None):
        """Create the deadlines of ``companies`` due in the horizon.

        The horizon starts at ``date_from`` (today by default) and spans
        the number of months of the company setting. Existing deadlines are
        kept: the unique key (rule, company, period end) makes the action
        safe to run again. A future deadline still to do whose rule no
        longer applies, after a change of the tax profile, is cancelled.
        Returns the created deadlines.
        """
        date_from = date_from or fields.Date.context_today(self)
        rules = self.env["l10n.ca.tax.deadline.rule"].search([])
        created = self.browse()
        for company in companies:
            months = company.l10n_ca_tax_deadline_horizon_months or 12
            date_to = date_from + relativedelta(months=months)
            existing = self.search([("company_id", "=", company.id)])
            keys = {(d.rule_id.id, d.period_end) for d in existing}
            values = []
            applicable = rules.filtered(lambda r, c=company: r._l10n_ca_applies(c))
            for rule in applicable:
                business_calendar = rule._l10n_ca_business_calendar(company)
                periods = rule._l10n_ca_periods(
                    company, date_from - relativedelta(months=LOOKBACK_MONTHS), date_to
                )
                for period_start, period_end in periods:
                    if (rule.id, period_end) in keys:
                        continue
                    due = rule._l10n_ca_due_date(company, period_end, business_calendar)
                    if not date_from <= due <= date_to:
                        continue
                    values.append(
                        {
                            "rule_id": rule.id,
                            "company_id": company.id,
                            "period_start": period_start,
                            "period_end": period_end,
                            "due_date": due,
                            "user_id": (
                                rule.user_id or company.l10n_ca_tax_deadline_user_id
                            ).id,
                        }
                    )
            created |= self.create(values)
            stale = existing.filtered(
                lambda d, a=applicable: (
                    d.state == "todo" and d.due_date >= date_from and d.rule_id not in a
                )
            )
            stale.action_cancel()
        return created

    @api.model
    def _l10n_ca_schedule_reminders(self, today=None):
        """Schedule a *Tax Deadline* activity on deadlines entering their window.

        The window opens ``l10n_ca_tax_deadline_reminder_days`` days before
        the due date. The activity is due on the due date and assigned to the
        responsible of the deadline, its summary written in the language of
        the responsible; a deadline without responsible gets no activity. ``reminder_sent`` keeps a reminder from being scheduled
        again once its activity is done or deleted.
        """
        today = today or fields.Date.context_today(self)
        candidates = self.search(
            [
                ("state", "=", "todo"),
                ("reminder_sent", "=", False),
                ("user_id", "!=", False),
            ]
        )
        for deadline in candidates:
            days = deadline.company_id.l10n_ca_tax_deadline_reminder_days
            if deadline.due_date - timedelta(days=max(days, 0)) > today:
                continue
            deadline_in_lang = deadline.with_context(
                lang=deadline.user_id.lang or self.env.lang
            )
            activity = deadline_in_lang.activity_schedule(
                "l10n_ca_tax_calendar.mail_activity_type_tax_deadline",
                date_deadline=deadline.due_date,
                summary=deadline_in_lang.rule_id.name,
                user_id=deadline.user_id.id,
            )
            deadline.write({"reminder_activity_id": activity.id, "reminder_sent": True})

    def action_generate_now(self):
        """Run the generation and the reminders for the current Canadian companies."""
        self._l10n_ca_generate(
            self.env.companies.filtered(lambda c: c.partner_id.country_id.code == "CA")
        )
        self._l10n_ca_schedule_reminders()
        return {"type": "ir.actions.client", "tag": "soft_reload"}
