from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AssignManifestLineWizard(models.TransientModel):
    _name = "transport.assign.manifest.line.wizard"

    wizard_id = fields.Many2one(
        "transport.assign.manifest.wizard",
        required=True,
        ondelete="cascade",
    )
    movement_leg_id = fields.Many2one("transport.movement.leg")
    booking_id = fields.Many2one(
        "transport.booking",
        store=True,
    )
    docket_no = fields.Char()
    booking_good_line_id = fields.Many2one("transport.goods.line")

    goods_type_id = fields.Many2one("transport.goods.type")
    unit_id = fields.Many2one("uom.uom")
    weight = fields.Float()

    available_qty = fields.Float()
    load_qty = fields.Float()

    @api.constrains('load_qty')
    def _check_load_qty(self):
        for record in self:
            if record.load_qty == 0:
                raise ValidationError("Load quantity cannot be 0. Please enter a valid quantity.")
