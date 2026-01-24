# ds_accounts/models/accounts_journal.py
from odoo import models, fields


class DsAccountJournal(models.Model):
    _name = "ds.accounts.journal"
    _description = "Accounting Journal"
    _order = "name"

    # Journal name (e.g., Sales, Purchase)
    name = fields.Char(string="Journal Name", required=True)

    # Short code (e.g., SALE, PUR, CASH)
    code = fields.Char(string="Journal Code", required=True)

    # Type of journal
    journal_type = fields.Selection(
        [
            ("sale", "Sales"),
            ("purchase", "Purchase"),
            ("cash", "Cash"),
            ("bank", "Bank"),
            ("general", "General"),
        ],
        string="Journal Type",
        required=True,
    )

    # Default accounts
    default_debit_account_id = fields.Many2one(
        "ds.accounts.account", string="Default Debit Account"
    )
    default_credit_account_id = fields.Many2one(
        "ds.accounts.account", string="Default Credit Account"
    )

    # Active / Inactive
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "Journal code must be unique!"),
    ]
