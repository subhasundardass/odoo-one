# ds_accounts/models/accounts_move_line.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DsAccountMoveLine(models.Model):
    _name = "ds.accounts.account.move.line"
    _description = "Journal Entry Line"

    move_id = fields.Many2one(
        "ds.accounts.account.move",
        string="Journal Entry",
        ondelete="cascade",
        required=True,
    )
    account_id = fields.Many2one("ds.accounts.account", string="Account", required=True)
    partner_id = fields.Many2one("res.partner", string="Partner")
    debit = fields.Float(string="Debit", default=0.0)
    credit = fields.Float(string="Credit", default=0.0)
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    # Optional: add reference / description
    name = fields.Char(string="Description")
    date = fields.Date(
        string="Entry Date",
        related="move_id.date",
        store=True,
        readonly=True,
    )

    @api.constrains("debit", "credit")
    def _check_debit_credit(self):
        for line in self:
            if line.debit < 0 or line.credit < 0:
                raise ValidationError("Debit and Credit amounts must be non-negative!")

            if line.debit == 0 and line.credit == 0:
                raise ValidationError(
                    "Either Debit or Credit must be greater than zero!"
                )

    @api.model
    def create(self, vals):
        if vals.get("debit", 0.0) < 0 or vals.get("credit", 0.0) < 0:
            raise ValidationError("Debit and Credit amounts must be non-negative!")
        if vals.get("debit", 0.0) == 0 and vals.get("credit", 0.0) == 0:
            raise ValidationError("Either Debit or Credit must be greater than zero!")
        return super().create(vals)

    def write(self, vals):
        if "debit" in vals and vals["debit"] < 0:
            raise ValidationError("Debit amount must be non-negative!")
        if "credit" in vals and vals["credit"] < 0:
            raise ValidationError("Credit amount must be non-negative!")
        if ("debit" in vals and vals["debit"] == 0) and (
            "credit" in vals and vals["credit"] == 0
        ):
            raise ValidationError("Either Debit or Credit must be greater than zero!")
        return super().write(vals)
