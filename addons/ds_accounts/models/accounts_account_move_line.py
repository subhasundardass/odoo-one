# ds_accounts/models/accounts_move_line.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DsAccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _description = "Journal Entry Line (TMS Extended)"

    # Optional: TMS specific fields (SAFE to add)
    trip_reference = fields.Char(string="Trip Reference")

    @api.constrains("debit", "credit")
    def _check_debit_credit_tms(self):
        """
        Extra safety validation (Odoo already enforces most rules,
        but this keeps your business logic explicit)
        """
        for line in self:
            if line.debit < 0 or line.credit < 0:
                raise ValidationError("Debit and Credit must be non-negative.")

            if line.debit and line.credit:
                raise ValidationError(
                    "A journal line cannot have both Debit and Credit."
                )

            if not line.debit and not line.credit:
                raise ValidationError(
                    "Either Debit or Credit must be greater than zero."
                )
