# ds_accounts/models/accounts_journal.py
from odoo import models, fields


class DsAccountJournal(models.Model):
    _inherit = "account.journal"  # inherit Odoo default journal
    _description = "Accounting Journal (Extended)"

    # Optional: Add TMS-specific default debit/credit accounts if needed
    default_debit_account_id = fields.Many2one(
        "account.account", string="Default Debit Account"
    )
    default_credit_account_id = fields.Many2one(
        "account.account", string="Default Credit Account"
    )
