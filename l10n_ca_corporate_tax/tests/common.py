# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class L10nCaCorporateTaxCommon(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ca")
    def setUpClass(cls):
        super().setUpClass()
        # Assertions read the English messages whatever languages the
        # database has loaded.
        cls.env = cls.env(context=dict(cls.env.context, lang="en_US"))
        cls.company = cls.company_data["company"]
        cls.company.write(
            {
                "fiscalyear_last_month": "12",
                "fiscalyear_last_day": 31,
                "l10n_ca_ccpc": True,
                "l10n_ca_instalment_frequency": "none",
                "l10n_ca_corporate_tax_user_id": cls.env.user.id,
            }
        )
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.misc_journal = cls.company_data["default_journal_misc"]
        cls.shareholder = cls.env["res.partner"].create(
            {"name": "Test Shareholder", "l10n_ca_shareholder": True}
        )

    @classmethod
    def _account(cls, code, account_type, **values):
        values.update(
            code=code,
            name=f"Test {code}",
            account_type=account_type,
            company_ids=[fields.Command.set(cls.company.ids)],
        )
        return cls.env["account.account"].create(values)

    @classmethod
    def _entry(cls, day, lines, journal=None):
        """Post a journal entry; ``lines`` is ``(account, partner, debit, credit)``."""
        move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": day,
                "journal_id": (journal or cls.misc_journal).id,
                "line_ids": [
                    fields.Command.create(
                        {
                            "name": "test",
                            "account_id": account.id,
                            "partner_id": partner.id if partner else False,
                            "debit": debit,
                            "credit": credit,
                        }
                    )
                    for account, partner, debit, credit in lines
                ],
            }
        )
        move.action_post()
        return move
