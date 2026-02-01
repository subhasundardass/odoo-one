from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountsCustomerReceipt(models.Model):
    _name = "ds.accounts.customer.receipt"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Customer Receipt"

    partner_id = fields.Many2one("res.partner", required=True)
    receipt_amount = fields.Monetary(required=True)
    journal_id = fields.Many2one(
        "account.journal",
        required=True,
        domain="[('type','in',('bank','cash'))]",
    )
    date = fields.Date(default=fields.Date.context_today)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    unpaid_invoice_ids = fields.Many2many(
        "account.move",
        compute="_compute_unpaid_invoices",
        readonly=True,
    )
    total_unpaid_amount = fields.Monetary(
        string="Total Unpaid Amount",
        compute="_compute_total_unpaid_amount",
        currency_field="currency_id",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
        ],
        default="draft",
        string="Status",
        tracking=True,
    )
    receipt_ref = fields.Char()

    @api.depends("unpaid_invoice_ids.amount_residual")
    def _compute_total_unpaid_amount(self):
        for rec in self:
            rec.total_unpaid_amount = sum(
                rec.unpaid_invoice_ids.mapped("amount_residual")
            )

    @api.depends("partner_id", "company_id")
    def _compute_unpaid_invoices(self):
        for rec in self:
            if not rec.partner_id:
                rec.unpaid_invoice_ids = False
                continue

            rec.unpaid_invoice_ids = self.env["account.move"].search(
                [
                    ("partner_id", "=", rec.partner_id.id),
                    ("company_id", "=", rec.company_id.id),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("payment_state", "in", ("not_paid", "partial")),
                ],
                order="invoice_date asc",
            )

    def action_post_receipt(self):
        for rec in self:
            if rec.receipt_amount <= 0:
                raise ValidationError("Receipt amount must be greater than zero.")

            if not rec.unpaid_invoice_ids:
                raise ValidationError("No unpaid invoices found.")

            remaining_amount = rec.receipt_amount

            # FIFO: oldest invoice first
            invoices = rec.unpaid_invoice_ids.sorted(
                key=lambda inv: inv.invoice_date or inv.date
            )

            for invoice in invoices:
                if remaining_amount <= 0:
                    break

                pay_amount = min(invoice.amount_residual, remaining_amount)

                wizard = (
                    self.env["account.payment.register"]
                    .with_context(
                        active_model="account.move",
                        active_ids=[invoice.id],
                    )
                    .create(
                        {
                            "amount": pay_amount,
                            "journal_id": rec.journal_id.id,
                            "payment_date": rec.date,
                        }
                    )
                )

                wizard.action_create_payments()

                remaining_amount -= pay_amount

            rec.state = "posted"
