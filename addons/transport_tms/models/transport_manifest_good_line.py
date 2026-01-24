from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare


class TransportManifestGoodLine(models.Model):
    _name = "transport.manifest.good.line"
    _description = "Manifest Goods Line"

    manifest_id = fields.Many2one(
        "transport.manifest", required=True, ondelete="cascade"
    )

    booking_id = fields.Many2one(
        "transport.booking",
        string="Booking",
        required=True,
    )
    movement_leg_id = fields.Many2one("transport.movement.leg", required=True)
    good_line_id = fields.Many2one("transport.goods.line", required=True)

    qty_loaded = fields.Float(required=True, default=0.00)
    qty_booked = fields.Float(required=True, default=0.00)
    qty_received = fields.Float(required=True, default=0.00)
    qty_remaining = fields.Float(required=True, default=0.00)

    unit = fields.Many2one(
        "uom.uom",
        string="UoM",
        related="good_line_id.unit_id",
        store=True,
        readonly=True,
    )
    docket_no = fields.Char(
        string="Docket No",
        related="booking_id.docket_no",
        store=True,
        readonly=True,
    )

    goods_type_id = fields.Many2one(
        "transport.goods.type",
        related="good_line_id.goods_type_id",
        store=True,
        readonly=True,
    )

    description = fields.Char(
        string="Goods Description",
        related="good_line_id.description",
        store=True,
        readonly=True,
    )

    from_location_id = fields.Many2one(
        "transport.location",
        string="From Location",
        required=True,
    )

    to_location_id = fields.Many2one(
        "transport.location",
        string="To Location",
        required=True,
    )

    status = fields.Selection(
        [
            ("full", "Fully Received"),
            ("partial", "Partially Received"),
            ("rejected", "Rejected"),
        ],
        required=True,
        default="full",
    )
