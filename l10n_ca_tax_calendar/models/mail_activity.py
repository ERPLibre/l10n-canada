# Copyright 2026 TechnoLibre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _action_done(self, feedback=False, attachment_ids=None):
        """Mark a tax deadline done when its reminder activity is done.

        Only activities of the *Tax Deadline* type close the deadline; any
        other activity scheduled on it leaves its state alone.
        """
        activity_type = self.env.ref(
            "l10n_ca_tax_calendar.mail_activity_type_tax_deadline",
            raise_if_not_found=False,
        )
        deadline_ids = [
            activity.res_id
            for activity in self
            if activity.res_model == "l10n.ca.tax.deadline"
            and activity_type
            and activity.activity_type_id == activity_type
        ]
        result = super()._action_done(feedback=feedback, attachment_ids=attachment_ids)
        if deadline_ids:
            deadlines = self.env["l10n.ca.tax.deadline"].browse(deadline_ids).exists()
            deadlines.filtered(lambda d: d.state == "todo")._l10n_ca_mark_done()
        return result
