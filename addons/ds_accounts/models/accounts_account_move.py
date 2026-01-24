# ds_accounts/models/accounts_move.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DsAccountMove(models.Model):
    _name = "ds.accounts.account.move"
    _description = "Journal Entry"
    _order = "date desc, id desc"

    name = fields.Char(string="Entry Reference", default="Draft", readonly=True)
    date = fields.Date(string="Entry Date", required=True, default=fields.Date.today)

    # journal_id = fields.Many2one("ds.accounts.journal", string="Journal", required=True)
    # Change journal to point to accounts.journal
    journal_id = fields.Many2one("accounts.journal", string="Journal", required=True)

    line_ids = fields.One2many(
        "ds.accounts.account.move.line",
        "move_id",
        string="Journal Items",
        required=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
        ],
        default="draft",
        string="Status",
    )

    @api.model
    def create(self, vals):
        # Assign a sequence-like name if needed
        vals["name"] = vals.get(
            "name", "JE/%s" % self.env["ds.accounts.move"].search_count([]) + 1
        )
        return super().create(vals)

    @api.model
    def create_journal_entry(
        self, name, amount, trip_type="local", partner_id=None, date=None
    ):
        """
        Automatically create a journal entry for a TMS trip
        """
        if amount <= 0:
            raise ValidationError("Amount must be greater than zero")

        if not date:
            date = fields.Date.today()

        # Pick journal based on trip type
        journal = self.env["accounts.journal"].search(
            [("trip_type", "=", trip_type)], limit=1
        )

        if not journal:
            raise ValidationError(f"No journal configured for trip type: {trip_type}")

        # Use default debit/credit accounts from the journal
        debit_account = journal.default_trip_debit_account_id
        credit_account = journal.default_trip_credit_account_id

        if not debit_account or not credit_account:
            raise ValidationError(
                f"Journal {journal.name} does not have default accounts set"
            )

        # Create the journal entry
        move = self.create(
            {
                "journal_id": journal.id,
                "date": date,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": debit_account.id,
                            "debit": amount,
                            "credit": 0.0,
                            "partner_id": partner_id,
                            "name": name,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": credit_account.id,
                            "debit": 0.0,
                            "credit": amount,
                            "partner_id": partner_id,
                            "name": name,
                        },
                    ),
                ],
            }
        )

        # Post the entry
        move.action_post()
        return move
