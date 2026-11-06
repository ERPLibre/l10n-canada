# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from collections import defaultdict
from datetime import date

from freezegun import freeze_time

from odoo.tests import TransactionCase, tagged

from ..hooks import post_init_hook
from ..tools import BusinessCalendar, add_months, calendar_periods, fiscal_periods

D = date.fromisoformat


@tagged("post_install", "-at_install")
class TestTaxCalendarTools(TransactionCase):
    def test_add_months_keeps_month_end(self):
        self.assertEqual(add_months(D("2027-01-31"), 1), D("2027-02-28"))
        self.assertEqual(add_months(D("2027-02-28"), 3), D("2027-05-31"))
        self.assertEqual(add_months(D("2028-02-29"), 12), D("2029-02-28"))
        self.assertEqual(add_months(D("2027-03-15"), 1), D("2027-04-15"))
        self.assertEqual(add_months(D("2026-12-31"), 0), D("2026-12-31"))

    def test_calendar_periods(self):
        halves = list(calendar_periods("semi_month", D("2027-02-01"), D("2027-02-28")))
        self.assertEqual(
            halves,
            [(D("2027-02-01"), D("2027-02-15")), (D("2027-02-16"), D("2027-02-28"))],
        )
        weeks = list(
            calendar_periods("quarter_month", D("2027-02-01"), D("2027-02-28"))
        )
        self.assertEqual([end.day for _start, end in weeks], [7, 14, 21, 28])
        quarters = list(calendar_periods("quarter", D("2026-11-01"), D("2027-06-30")))
        self.assertEqual(
            [end for _start, end in quarters],
            [D("2026-12-31"), D("2027-03-31"), D("2027-06-30")],
        )

    def test_fiscal_periods_short_last_period(self):
        """A fiscal year of 10 months cut in quarters ends with a 1-month period."""

        def fiscal_year_dates(day):
            return D("2027-01-01"), D("2027-10-31")

        periods = list(
            fiscal_periods(fiscal_year_dates, 3, D("2027-01-01"), D("2027-10-31"))
        )
        self.assertEqual(periods[-1], (D("2027-10-01"), D("2027-10-31")))
        self.assertEqual(len(periods), 4)

    def test_business_calendar(self):
        holidays = {D("2026-12-25"), D("2026-12-28")}
        cal = BusinessCalendar(lambda year: holidays)
        # Friday Dec 25 is a holiday, then the weekend, then Monday holiday.
        self.assertEqual(cal.next_business_day(D("2026-12-25")), D("2026-12-29"))
        self.assertEqual(cal.add_business_days(D("2026-12-24"), 1), D("2026-12-29"))
        self.assertEqual(cal.add_business_days(D("2026-12-24"), 0), D("2026-12-24"))


@tagged("post_install", "-at_install")
class TestTaxCalendar(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref("base.CAD").active = True
        cls.user = cls.env.user
        cls.company = cls.env["res.company"].create(
            {
                "name": "Calendar test company",
                "currency_id": cls.env.ref("base.CAD").id,
                "country_id": cls.env.ref("base.ca").id,
                "state_id": cls.env.ref("base.state_ca_qc").id,
                "fiscalyear_last_month": "12",
                "fiscalyear_last_day": 31,
                "l10n_ca_ccpc": True,
                "l10n_ca_gst_filing_frequency": "annual",
                "l10n_ca_qst_filing_frequency": "annual",
                "l10n_ca_gst_prior_net_tax": 5000.0,
                "l10n_ca_qst_prior_net_tax": 5000.0,
                "l10n_ca_instalment_frequency": "quarterly",
                "l10n_ca_payroll_remitter_type": "regular",
                "l10n_ca_tax_deadline_user_id": cls.user.id,
                "l10n_ca_tax_deadline_reminder_days": 14,
                "l10n_ca_tax_deadline_horizon_months": 12,
            }
        )
        cls.user.company_ids |= cls.company
        cls.Deadline = cls.env["l10n.ca.tax.deadline"]
        cls.today = D("2026-10-26")

    def _rule(self, code):
        return self.env.ref(f"l10n_ca_tax_calendar.rule_{code}")

    def _due_dates(self, deadlines):
        result = defaultdict(list)
        for deadline in deadlines.sorted("due_date"):
            result[deadline.rule_id.code].append(deadline.due_date)
        return result

    def test_instalment_threshold(self):
        """Threshold 3,000 (shipped parameter): 2,999.99 does not reach it."""
        self.assertTrue(self.company.l10n_ca_gst_instalments_required)
        self.company.l10n_ca_gst_prior_net_tax = 2999.99
        self.assertFalse(self.company.l10n_ca_gst_instalments_required)
        self.company.l10n_ca_gst_prior_net_tax = 3000.0
        self.assertTrue(self.company.l10n_ca_gst_instalments_required)
        self.company.l10n_ca_gst_prior_net_tax = 0.0
        self.assertFalse(self.company.l10n_ca_gst_instalments_required)

    def test_rule_description_in_french(self):
        """The legal rule shown on a deadline follows the user language.

        Every shipped rule has a French description in i18n/fr.po, read
        through the related field of the deadline as well.
        """
        self.env["res.lang"]._activate_lang("fr_CA")
        self.env["ir.module.module"]._load_module_terms(
            ["l10n_ca_tax_calendar"], ["fr_CA"]
        )
        rules = self.env["l10n.ca.tax.deadline.rule"].search([])
        self.assertEqual(len(rules), 35)
        for rule in rules:
            english = rule.with_context(lang="en_US").description
            french = rule.with_context(lang="fr_CA").description
            self.assertTrue(english and french, rule.code)
            self.assertNotEqual(english, french, rule.code)
        deadline = self.Deadline.create(
            {
                "rule_id": self._rule("t2_return").id,
                "company_id": self.company.id,
                "period_start": D("2026-01-01"),
                "period_end": D("2026-12-31"),
                "due_date": D("2027-06-30"),
            }
        )
        self.assertTrue(
            deadline.with_context(lang="fr_CA").rule_description.startswith(
                "Déclaration exigible dans les six mois"
            )
        )

    def test_generated_deadlines(self):
        """Horizon 2026-10-26 to 2027-10-26, fiscal year ending December 31.

        Weekend shifts (next business day): 2026-10-31 Sat -> 11-02,
        2026-11-15 Sun -> 11-16, 2027-01-31 Sun -> 02-01, 2027-02-28 Sun ->
        03-01, 2027-05-15 Sat -> 05-17, 2027-07-31 Sat -> 08-02 (the Civic
        Holiday of 2027-08-02 does not apply in Quebec), 2027-08-15 Sun ->
        08-16. The Registraire and CNESST rules do not shift.
        """
        created = self.Deadline._l10n_ca_generate(self.company, date_from=self.today)
        dues = self._due_dates(created)
        instalments = [
            D("2026-11-02"),
            D("2027-02-01"),
            D("2027-04-30"),
            D("2027-08-02"),
        ]
        self.assertEqual(dues["gst_instalment"], instalments)
        self.assertEqual(dues["qst_instalment"], instalments)
        self.assertEqual(dues["gst_return_annual"], [D("2027-03-31")])
        self.assertEqual(dues["qst_return_annual"], [D("2027-03-31")])
        # 2027-09-30 is the National Day for Truth and Reconciliation, a
        # federal holiday only: the CRA instalment moves to Fri 10-01.
        quarter_ends = [D("2026-12-31"), D("2027-03-31"), D("2027-06-30")]
        self.assertEqual(
            dues["cit_instalment_quarterly_federal"], quarter_ends + [D("2027-10-01")]
        )
        self.assertEqual(
            dues["cit_instalment_quarterly_quebec"], quarter_ends + [D("2027-09-30")]
        )
        # CCPC: three months federally, two months in Quebec (Feb 28 Sunday).
        self.assertEqual(dues["cit_balance_federal_ccpc"], [D("2027-03-31")])
        self.assertEqual(dues["cit_balance_quebec"], [D("2027-03-01")])
        self.assertEqual(dues["t2_return"], [D("2027-06-30")])
        self.assertEqual(dues["co17_return"], [D("2027-06-30")])
        payroll = [
            D("2026-11-16"),
            D("2026-12-15"),
            D("2027-01-15"),
            D("2027-02-15"),
            D("2027-03-15"),
            D("2027-04-15"),
            D("2027-05-17"),
            D("2027-06-15"),
            D("2027-07-15"),
            D("2027-08-16"),
            D("2027-09-15"),
            D("2027-10-15"),
        ]
        self.assertEqual(dues["payroll_federal_regular"], payroll)
        self.assertEqual(dues["payroll_quebec_monthly"], payroll)
        for code in ("t4_summary", "rl1_summary", "hsf_reconciliation"):
            self.assertEqual(dues[code], [D("2027-03-01")], code)
        # CNESST: before March 15, so March 14, with no weekend shift.
        self.assertEqual(dues["cnesst_wages"], [D("2027-03-14")])
        self.assertEqual(dues["req_annual_update_combined"], [D("2027-06-30")])
        self.assertEqual(dues["req_fee_combined"], [D("2027-02-28")])
        not_applicable = {
            "gst_return_monthly",
            "gst_return_quarterly",
            "cit_instalment_monthly_federal",
            "cit_balance_federal",
            "payroll_federal_accelerated_1",
            "t5_summary",
            "rl3_summary",
            "req_annual_update",
        }
        self.assertFalse(not_applicable & set(dues))
        self.assertEqual(len(created), 52)
        self.assertEqual(set(created.mapped("user_id")), {self.user})
        self.assertEqual(
            created.filtered(lambda d: d.rule_id.code == "gst_instalment")[
                0
            ].period_end,
            D("2026-09-30"),
        )

    def test_generation_is_idempotent(self):
        self.Deadline._l10n_ca_generate(self.company, date_from=self.today)
        again = self.Deadline._l10n_ca_generate(self.company, date_from=self.today)
        self.assertFalse(again)

    def test_profile_change_cancels_stale_deadlines(self):
        first = self.Deadline._l10n_ca_generate(self.company, date_from=self.today)
        self.company.l10n_ca_gst_filing_frequency = "quarterly"
        second = self.Deadline._l10n_ca_generate(self.company, date_from=self.today)
        stale = first.filtered(
            lambda d: d.rule_id.code in ("gst_return_annual", "gst_instalment")
        )
        self.assertEqual(set(stale.mapped("state")), {"cancel"})
        # Quarter ending 2026-09-30 is due 2026-10-31 (Sat) -> 2026-11-02.
        self.assertEqual(
            self._due_dates(second)["gst_return_quarterly"][0], D("2026-11-02")
        )

    def test_holidays_by_jurisdiction(self):
        """Business days count past the holidays of the authority only.

        Weekly period ending Sat 2026-11-07, due the 3rd business day after:
        CRA skips Remembrance Day (Wed 11-11) -> Mon 9, Tue 10, Thu 12;
        Revenu Quebec does not -> Mon 9, Tue 10, Wed 11.
        """
        self.company.l10n_ca_payroll_remitter_type = "accelerated_2"
        federal = self._rule("payroll_federal_accelerated_2")
        quebec = self._rule("payroll_quebec_weekly")
        self.assertEqual(
            federal._l10n_ca_due_date(self.company, D("2026-11-07")), D("2026-11-12")
        )
        self.assertEqual(
            quebec._l10n_ca_due_date(self.company, D("2026-11-07")), D("2026-11-11")
        )
        # Period ending Sun 2026-06-21: Mon 22, Tue 23, Wed 24 is the
        # Quebec National Holiday for both authorities, then Thu 25.
        self.assertEqual(
            federal._l10n_ca_due_date(self.company, D("2026-06-21")), D("2026-06-25")
        )
        self.assertEqual(
            quebec._l10n_ca_due_date(self.company, D("2026-06-21")), D("2026-06-25")
        )
        # Period ending 2025-12-31: Jan 1 holiday, Fri 2, Mon 5, Tue 6.
        # Revenu Quebec is closed on Jan 2: Mon 5, Tue 6, Wed 7.
        self.assertEqual(
            federal._l10n_ca_due_date(self.company, D("2025-12-31")), D("2026-01-06")
        )
        self.assertEqual(
            quebec._l10n_ca_due_date(self.company, D("2025-12-31")), D("2026-01-07")
        )
        # Period Dec 15-21 2026: the CRA counts Tue 22, Wed 23, Thu 24.
        # Revenu Quebec is closed on Dec 24, 25 and 28 (Boxing Day moved):
        # Tue 22, Wed 23, Tue 29, the date of its published 2026 calendar.
        self.assertEqual(
            federal._l10n_ca_due_date(self.company, D("2026-12-21")), D("2026-12-24")
        )
        self.assertEqual(
            quebec._l10n_ca_due_date(self.company, D("2026-12-21")), D("2026-12-29")
        )
        # The closures of Revenu Quebec do not move its other deadlines:
        # the income tax instalment of Thu 2026-12-31 stays on that day.
        self.assertEqual(
            self._rule("cit_instalment_quarterly_quebec")._l10n_ca_due_date(
                self.company, D("2026-12-31")
            ),
            D("2026-12-31"),
        )

    def test_christmas_and_boxing_day(self):
        """Half-month Dec 1-15 2026 due the 25th (Fri, Christmas).

        CRA: Fri 25 Christmas, Sat 26, Sun 27 -> Mon 2026-12-28. Revenu
        Quebec is also closed on Mon 28, where Boxing Day is moved ->
        Tue 2026-12-29.
        """
        federal = self._rule("payroll_federal_accelerated_1")
        quebec = self._rule("payroll_quebec_twice_monthly")
        self.assertEqual(
            federal._l10n_ca_due_date(self.company, D("2026-12-15")), D("2026-12-28")
        )
        self.assertEqual(
            quebec._l10n_ca_due_date(self.company, D("2026-12-15")), D("2026-12-29")
        )
        # Second half of November: 10th of December (Thu), no shift.
        self.assertEqual(
            federal._l10n_ca_due_date(self.company, D("2026-11-30")), D("2026-12-10")
        )

    def test_non_calendar_fiscal_year(self):
        """Fiscal year ending June 30.

        FY ending 2027-06-30: GST annual return three months later is
        2027-09-30 (Thu), the National Day for Truth and Reconciliation, a
        federal holiday -> Fri 2027-10-01. Quebec balance two months later:
        2027-08-31 (Tue). T2 six months later: 2027-12-31 (Fri).
        """
        self.company.write({"fiscalyear_last_month": "6", "fiscalyear_last_day": 30})
        rule = self._rule("gst_return_annual")
        periods = rule._l10n_ca_periods(self.company, D("2027-01-01"), D("2027-12-31"))
        self.assertEqual(periods, [(D("2026-07-01"), D("2027-06-30"))])
        self.assertEqual(
            rule._l10n_ca_due_date(self.company, D("2027-06-30")), D("2027-10-01")
        )
        self.assertEqual(
            self._rule("cit_balance_quebec")._l10n_ca_due_date(
                self.company, D("2027-06-30")
            ),
            D("2027-08-31"),
        )
        self.assertEqual(
            self._rule("t2_return")._l10n_ca_due_date(self.company, D("2027-06-30")),
            D("2027-12-31"),
        )
        quarters = self._rule("cit_instalment_quarterly_federal")._l10n_ca_periods(
            self.company, D("2026-07-01"), D("2027-06-30")
        )
        self.assertEqual(
            [end for _start, end in quarters],
            [D("2026-09-30"), D("2026-12-31"), D("2027-03-31"), D("2027-06-30")],
        )

    def test_dated_timing_parameter(self):
        """A company version of the timing wins from its effective date only."""
        self.env["base.time.parameter"].create(
            {
                "name": "T2 timing test",
                "code": "l10n_ca.tax_calendar.timing_t2_return",
                "type": "json",
                "company_id": self.company.id,
                "version_ids": [
                    (0, 0, {"date_from": "2027-01-01", "value": '{"months": 5}'})
                ],
            }
        )
        rule = self._rule("t2_return")
        # Period ending 2026-12-31 still uses the shipped 6 months.
        self.assertEqual(
            rule._l10n_ca_due_date(self.company, D("2026-12-31")), D("2027-06-30")
        )
        # Period ending 2027-12-31: 5 months -> 2028-05-31 (Wed).
        self.assertEqual(
            rule._l10n_ca_due_date(self.company, D("2027-12-31")), D("2028-05-31")
        )

    def test_rule_fields_without_parameter(self):
        """A user rule without parameter: last day of February, no shift."""
        rule = self.env["l10n.ca.tax.deadline.rule"].create(
            {
                "name": "Custom yearly filing",
                "code": "test_custom",
                "authority": "rq",
                "category": "payroll",
                "period_type": "year",
                "fixed_month": 2,
                "fixed_day": 31,
                "due_date_shift": "none",
            }
        )
        self.assertEqual(
            rule._l10n_ca_due_date(self.company, D("2027-12-31")), D("2028-02-29")
        )
        rule.write({"fixed_month": 0, "offset_months": 1, "offset_days": 5})
        self.assertEqual(
            rule._l10n_ca_due_date(self.company, D("2027-01-31")), D("2027-03-05")
        )

    def test_reminders(self):
        """Reminder 14 days ahead: on 2026-10-26 only the deadlines due by
        2026-11-09 get an activity, the two sales tax instalments of 11-02."""
        deadlines = self.Deadline._l10n_ca_generate(self.company, date_from=self.today)
        self.Deadline._l10n_ca_schedule_reminders(today=self.today)
        reminded = deadlines.filtered("reminder_sent")
        self.assertEqual(
            set(reminded.mapped("rule_id.code")), {"gst_instalment", "qst_instalment"}
        )
        activity = reminded[0].reminder_activity_id
        self.assertEqual(activity.date_deadline, D("2026-11-02"))
        self.assertEqual(activity.user_id, self.user)
        self.Deadline._l10n_ca_schedule_reminders(today=self.today)
        self.assertEqual(len(reminded.activity_ids), 2)
        # Marking the activity done closes the deadline.
        activity.action_feedback(feedback="Paid")
        self.assertEqual(reminded[0].state, "done")
        self.assertTrue(reminded[0].reminder_sent)
        # Marking the deadline done closes its activity.
        reminded[1].action_done()
        self.assertEqual(reminded[1].state, "done")
        self.assertFalse(reminded[1].activity_ids)

    def test_name_and_reminder_follow_the_language(self):
        """A deadline created in English reads in French for a French user.

        The reminder summary takes the language of the responsible, not the
        one of the scheduled action that creates it.
        """
        self.env["res.lang"]._activate_lang("fr_CA")
        self.env["ir.module.module"]._load_module_terms(
            ["l10n_ca_tax_calendar"], ["fr_CA"]
        )
        self.user.lang = "fr_CA"
        deadlines = self.Deadline.with_context(lang="en_US")._l10n_ca_generate(
            self.company, date_from=self.today
        )
        deadline = deadlines.filtered(lambda d: d.rule_id.code == "t2_return")
        self.assertTrue(
            deadline.with_context(lang="en_US").name.startswith("T2 corporation")
        )
        self.assertTrue(
            deadline.with_context(lang="fr_CA").name.startswith(
                "Déclaration de revenus des sociétés T2"
            )
        )
        found = self.Deadline.with_context(lang="fr_CA").search(
            [("company_id", "=", self.company.id), ("name", "ilike", "sociétés T2")]
        )
        self.assertEqual(found, deadline)
        self.Deadline.with_context(lang="en_US")._l10n_ca_schedule_reminders(
            today=self.today
        )
        activity = deadlines.filtered("reminder_sent")[0].reminder_activity_id
        self.assertTrue(activity.summary.startswith("Acompte provisionnel"))

    @freeze_time("2026-10-26")
    def test_overdue_search(self):
        # is_overdue compares with the current date: the clock is frozen at
        # self.today so that only the back-dated deadline is overdue.
        deadlines = self.Deadline._l10n_ca_generate(self.company, date_from=self.today)
        deadline = deadlines[0]
        deadline.due_date = D("2020-01-01")
        overdue = self.Deadline.search(
            [("is_overdue", "=", True), ("company_id", "=", self.company.id)]
        )
        self.assertEqual(overdue, deadline)
        not_overdue = self.Deadline.search(
            [("is_overdue", "=", False), ("company_id", "=", self.company.id)]
        )
        self.assertNotIn(deadline, not_overdue)
        self.assertEqual(len(not_overdue), len(deadlines) - 1)

    def test_cron_runs(self):
        self.Deadline._cron_generate()
        self.assertTrue(self.Deadline.search([("company_id", "=", self.company.id)]))

    def test_quebec_instalment_frequency(self):
        """A Quebec frequency of its own drives the Quebec instalments only.

        Monthly fiscal periods from October 2026: weekend shifts 2026-10-31
        Sat -> 11-02, 2027-01-31 Sun -> 02-01, 2027-02-28 Sun -> 03-01,
        2027-07-31 Sat -> 08-02.
        """
        self.company.l10n_ca_qc_instalment_frequency = "monthly"
        dues = self._due_dates(
            self.Deadline._l10n_ca_generate(self.company, date_from=self.today)
        )
        self.assertEqual(
            dues["cit_instalment_monthly_quebec"],
            [
                D("2026-11-02"),
                D("2026-11-30"),
                D("2026-12-31"),
                D("2027-02-01"),
                D("2027-03-01"),
                D("2027-03-31"),
                D("2027-04-30"),
                D("2027-05-31"),
                D("2027-06-30"),
                D("2027-08-02"),
                D("2027-08-31"),
                D("2027-09-30"),
            ],
        )
        self.assertEqual(len(dues["cit_instalment_quarterly_federal"]), 4)
        self.assertFalse(
            {"cit_instalment_quarterly_quebec", "cit_instalment_monthly_federal"}
            & set(dues)
        )

    def test_quebec_instalment_frequency_none(self):
        self.company.l10n_ca_qc_instalment_frequency = "none"
        dues = self._due_dates(
            self.Deadline._l10n_ca_generate(self.company, date_from=self.today)
        )
        self.assertEqual(len(dues["cit_instalment_quarterly_federal"]), 4)
        self.assertFalse(
            {"cit_instalment_quarterly_quebec", "cit_instalment_monthly_quebec"}
            & set(dues)
        )

    def test_quebec_annual_remitter(self):
        """Annual remitter: the year 2026 is due Fri 2027-01-15."""
        self.company.l10n_ca_qc_remitter_type = "annual"
        created = self.Deadline._l10n_ca_generate(self.company, date_from=self.today)
        dues = self._due_dates(created)
        self.assertEqual(dues["payroll_quebec_annual"], [D("2027-01-15")])
        self.assertFalse(
            {"payroll_quebec_monthly", "payroll_quebec_quarterly"} & set(dues)
        )
        self.assertEqual(dues["rl1_summary"], [D("2027-03-01")])


@tagged("post_install", "-at_install")
class TestTaxCalendarHolidays(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Holiday = cls.env["calendar.public.holiday"]
        cls.canada = cls.env.ref("base.ca")

    def _holidays(self, year):
        return self.Holiday.search(
            [("year", "=", year), ("country_id", "=", self.canada.id)]
        )

    def test_installed_holidays(self):
        self.assertEqual(len(self._holidays(2026).line_ids), 17)
        line = self._holidays(2026).line_ids.filtered(
            lambda h: h.date == D("2026-06-24")
        )
        self.assertEqual(line.state_ids, self.env.ref("base.state_ca_qc"))

    def test_loader_completes_an_existing_year(self):
        """A year already present is completed, never duplicated.

        The public holiday 2026 of Canada exists with three lines: Boxing
        Day without province, and the Quebec National Holiday for Ontario
        only, which does not cover the shipped Quebec line.
        """
        self._holidays(2026).unlink()
        ontario = self.env.ref("base.state_ca_on")
        existing = self.Holiday.create(
            {
                "year": 2026,
                "country_id": self.canada.id,
                "line_ids": [
                    (0, 0, {"name": "Lendemain de Noel", "date": "2026-12-26"}),
                    (0, 0, {"name": "Noel", "date": "2026-12-25"}),
                    (
                        0,
                        0,
                        {
                            "name": "Test holiday",
                            "date": "2026-06-24",
                            "state_ids": [(6, 0, ontario.ids)],
                        },
                    ),
                ],
            }
        )
        created = self.Holiday._l10n_ca_load_holidays()
        self.assertEqual(self._holidays(2026), existing)
        self.assertEqual(len(created.filtered(lambda h: h.date.year == 2026)), 15)
        self.assertEqual(len(existing.line_ids), 18)
        boxing = existing.line_ids.filtered(lambda h: h.date == D("2026-12-26"))
        self.assertEqual(boxing.name, "Lendemain de Noel")
        self.assertEqual(boxing.l10n_ca_jurisdiction, "federal")
        june_24 = existing.line_ids.filtered(lambda h: h.date == D("2026-06-24"))
        self.assertEqual(len(june_24), 2)
        self.assertIn(self.env.ref("base.state_ca_qc"), june_24.state_ids)
        # A second run, and the install hook, change nothing.
        self.assertFalse(self.Holiday._l10n_ca_load_holidays())
        post_init_hook(self.env)
        self.assertEqual(len(existing.line_ids), 18)
        self.assertEqual(len(self._holidays(2027).line_ids), 16)
