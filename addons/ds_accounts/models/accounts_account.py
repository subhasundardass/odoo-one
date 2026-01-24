# ds_accounts/models/accounts_account.py
from odoo import models, fields


class DsAccountAccount(models.Model):
    _name = "ds.accounts.account"
    _description = "Chart of Accounts"
    _order = "code"

    # Account code (unique)
    code = fields.Char(
        string="Account Code",
        required=True,
    )

    # Account name
    name = fields.Char(
        string="Account Name",
        required=True,
    )

    # Account type
    account_type = fields.Selection(
        [
            ("asset", "Asset"),
            ("liability", "Liability"),
            ("income", "Income"),
            ("expense", "Expense"),
            ("equity", "Equity"),
        ],
        string="Account Type",
        required=True,
    )

    # Parent account for hierarchy
    parent_id = fields.Many2one(
        "ds.accounts.account", string="Parent Account", ondelete="restrict"
    )
    child_ids = fields.One2many(
        "ds.accounts.account", "parent_id", string="Child Accounts"
    )

    # Active / Inactive
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "Account code must be unique!"),
    ]
