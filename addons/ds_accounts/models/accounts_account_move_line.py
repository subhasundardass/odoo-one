# ds_accounts/models/accounts_move_line.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DsAccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _description = "Journal Entry Line (TMS Extended)"
