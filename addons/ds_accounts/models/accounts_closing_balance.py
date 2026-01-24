from odoo import models, fields, api
from odoo.exceptions import UserError


class DsAccountClosingBalance(models.Model):
    _name = "ds.accounts.closing.balance"
    _description = "Daily Closing Balance"
    _order = "date, account_id"
    _sql_constraints = [
        (
            "uniq_daily_balance",
            "unique(date, account_id, partner_id)",
            "Daily balance already exists for this account and partner.",
        )
    ]

    date = fields.Date(required=True, index=True)
    account_id = fields.Many2one("ds.account.account", required=True, index=True)
    partner_id = fields.Many2one("res.partner", index=True)

    opening_balance = fields.Float(string="Opening Balance")
    debit = fields.Float(string="Debit")
    credit = fields.Float(string="Credit")
    closing_balance = fields.Float(string="Closing Balance")

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )

    @api.model
    def compute_closing_balance(self, date):
        """
        Compute closing balance for all accounts for a given date.
        Intended to be called by cron or manually.
        """
        if not date:
            raise UserError("Date is required to compute closing balance")

        prev_date = fields.Date.subtract(date, days=1)

        accounts = self.env["ds.account.account"].search([])

        for account in accounts:
            # Previous closing balance
            prev_balance = self.search(
                [
                    ("date", "=", prev_date),
                    ("account_id", "=", account.id),
                    ("partner_id", "=", False),
                ],
                limit=1,
            )

            opening = prev_balance.closing_balance if prev_balance else 0.0

            # Sum today's journal entries
            domain = [
                ("date", "=", date),
                ("account_id", "=", account.id),
            ]
            lines = self.env["ds.account.move.line"].search(domain)

            debit = sum(lines.mapped("debit"))
            credit = sum(lines.mapped("credit"))

            closing = opening + debit - credit

            # Create or update daily balance
            record = self.search(
                [
                    ("date", "=", date),
                    ("account_id", "=", account.id),
                    ("partner_id", "=", False),
                ],
                limit=1,
            )

            vals = {
                "opening_balance": opening,
                "debit": debit,
                "credit": credit,
                "closing_balance": closing,
            }

            if record:
                record.write(vals)
            else:
                vals.update(
                    {
                        "date": date,
                        "account_id": account.id,
                    }
                )
                self.create(vals)

    @api.model
    def compute_partner_closing_balance(self, date):
        """
        Optional: Compute partner-wise closing balance (customer/vendor ledger)
        """
        prev_date = fields.Date.subtract(date, days=1)

        lines = self.env["ds.account.move.line"].search(
            [("date", "=", date), ("partner_id", "!=", False)]
        )

        for line in lines:
            prev_balance = self.search(
                [
                    ("date", "=", prev_date),
                    ("account_id", "=", line.account_id.id),
                    ("partner_id", "=", line.partner_id.id),
                ],
                limit=1,
            )

            opening = prev_balance.closing_balance if prev_balance else 0.0

            debit = line.debit
            credit = line.credit
            closing = opening + debit - credit

            record = self.search(
                [
                    ("date", "=", date),
                    ("account_id", "=", line.account_id.id),
                    ("partner_id", "=", line.partner_id.id),
                ],
                limit=1,
            )

            vals = {
                "opening_balance": opening,
                "debit": debit,
                "credit": credit,
                "closing_balance": closing,
            }

            if record:
                record.write(vals)
            else:
                vals.update(
                    {
                        "date": date,
                        "account_id": line.account_id.id,
                        "partner_id": line.partner_id.id,
                    }
                )
                self.create(vals)
