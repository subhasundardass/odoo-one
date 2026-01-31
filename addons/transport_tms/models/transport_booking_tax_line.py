from odoo import fields, models

class TransportBookingTaxLine(models.Model):
    _name = "transport.booking.tax.line"
    _description = "Booking Tax Line"

    booking_id = fields.Many2one(
        "transport.booking",
        string="Booking",
        ondelete="cascade",
        required=True,
    )

    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        required=True,
        domain=[("type_tax_use", "=", "sale")],
    )

    amount = fields.Monetary(
        string="Tax Amount",
        currency_field="currency_id",
        readonly=True,
    )

    currency_id = fields.Many2one(
        related="booking_id.currency_id",
        store=True,
    )