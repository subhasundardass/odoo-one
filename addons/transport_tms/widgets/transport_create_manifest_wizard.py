from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class TransportCreateManifestWizard(models.TransientModel):
    _name = "transport.create.manifest.wizard"
    _description = "Create Manifest Wizard"

    date = fields.Date(required=True)
    pickup_location_id = fields.Many2one("transport.location", required=True)
    destination_location_id = fields.Many2one("transport.location", required=True)
    vehicle_id = fields.Many2one("fleet.vehicle", required=True)
    good_line_ids = fields.One2many(
        "transport.create.manifest.good.wizard", "wizard_id", string="Goods"
    )

    @api.onchange("pickup_location_id", "destination_location_id")
    def pupulate_goods(self):
        self.ensure_one()
        # 1️⃣ Find eligible legs
        legs = self.env["transport.movement.leg"].search(
            [
                ("from_location_id", "=", self.pickup_location_id.id),
                ("to_location_id", "=", self.destination_location_id.id),
                ("state", "=", "planned"),
                # ("manifest_id", "=", False),
            ]
        )
        if not self.id:
            self.write({})
        # self.good_line_ids.unlink()
        lines = []
        for leg in legs:

            for good in leg.movement_id.booking_id.goods_line_ids:
                # remaining_qty = good.qty - good.loaded_qty
                if good.qty <= 0:
                    continue
                _logger.warning("GOOD ID = %s", good.goods_type_id)
                lines.append(
                    (
                        0,
                        0,
                        {
                            # "wizard_id": self.id,
                            "leg_id": leg.exists() and leg.id or False,
                            "good_id": good.id,
                            "good_loaded_qty": 0.0,
                        },
                    )
                )

        self.good_line_ids = lines

    def action_populate_goods(self):
        self.ensure_one()

        if not self.id:
            self = self.create(self._convert_to_write(self._cache))

        # 1️⃣ Find eligible legs
        legs = self.env["transport.movement.leg"].search(
            [
                ("from_location_id", "=", self.pickup_location_id.id),
                ("to_location_id", "=", self.destination_location_id.id),
                # ("state", "=", "planned"),
                # ("manifest_id", "=", False),
            ]
        )

        # 2️⃣ Clear old lines
        self.good_line_ids.unlink()

        lines = []
        for leg in legs:

            for good in leg.movement_id.booking_id.goods_line_ids:
                # remaining_qty = good.qty - good.loaded_qty
                if good.qty <= 0:
                    continue

                lines.append(
                    (
                        0,
                        0,
                        {
                            "leg_id": leg.exists() and leg.id or False,
                            "good_line_id": good.exists() and good.id or False,
                            "available_qty": good.qty,
                            "load_qty": 0,
                            "uom_id": good.unit_id.exists()
                            and good.unit_id.id
                            or False,
                        },
                    )
                )

        _logger.warning("SELF ID = %s", self.id)
        self.write({"good_line_ids": lines})

        # _logger.warning("WIZARD ID = %s", self.ids[0])
        return {
            "type": "ir.actions.act_window",
            "name": "Create Manifest",
            "res_model": "transport.create.manifest.wizard",
            # "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class TransportCreateManifestGoodWizard(models.TransientModel):
    _name = "transport.create.manifest.good.wizard"
    _description = "Manifest Goods Wizard Line"

    wizard_id = fields.Many2one("transport.create.manifest.wizard", ondelete="cascade")

    leg_id = fields.Many2one("transport.movement.leg", readonly=True)
    good_id = fields.Many2one(
        "transport.goods.line",
        string="Good",
        required=True,
        readonly=True,
    )
    booking_id = fields.Many2one(
        "transport.booking",
        related="good_id.booking_id",
        string="Booking No",
        readonly=True,
    )
    docket_no = fields.Char(
        related="good_id.booking_id.docket_no",
        string="Docket No",
        readonly=True,
    )
    good_type_id = fields.Many2one(
        "transport.goods.type",
        related="good_id.goods_type_id",
        string="Good Type",
        readonly=True,
    )
    good_available_qty = fields.Float(
        related="good_id.qty",
        string="Available Qty",
        readonly=True,
    )

    good_loaded_qty = fields.Float(
        string="Load Qty",
        required=True,
        default=0.0,
    )
    good_unit = fields.Many2one(
        "uom.uom",
        related="good_id.unit_id",
        string="Unit",
        readonly=True,
    )

    # available_qty = fields.Float(readonly=True)
    # load_qty = fields.Float()
    # uom_id = fields.Many2one("uom.uom", readonly=True)
