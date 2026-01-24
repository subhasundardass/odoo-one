from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class TransportManifest(models.Model):
    _name = "transport.manifest"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Internal Transfer Manifest"
    _order = "id desc"

    name = fields.Char(
        string="Manifest No",
        required=True,
        copy=False,
        readonly=True,
        default="New",
        tracking=True,
    )

    manifest_type = fields.Selection(
        [
            ("internal", "Internal Transfer"),
            ("vendor", "Vendor Inbound"),
        ],
        default="internal",
        required=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("receivable", "Hub Receivable"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )

    source_location_id = fields.Many2one("transport.location", string="From")
    destination_location_id = fields.Many2one("transport.location", string="To")

    vehicle_id = fields.Many2one("fleet.vehicle", string="Vehicle")
    driver_id = fields.Many2one("res.partner", string="Driver")

    leg_ids = fields.Many2many("transport.movement.leg", string="Movement Legs")
    movement_leg_id = fields.Many2one("transport.movement.leg", string="Movement Leg")
    movement_id = fields.Many2one(
        "transport.movement", related="movement_leg_id.movement_id", store=False
    )

    estimated_cost = fields.Float()
    departure_time = fields.Datetime()
    arrival_time = fields.Datetime()

    manifest_good_line_ids = fields.One2many(
        "transport.manifest.good.line",
        "manifest_id",
        string="Manifest Goods",
        ondelete="cascade",
    )

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("transport.manifest") or "New"
            )
            return super().create(vals)

    # --------------------------------------
    #    Action Hub receive
    # ---------------------------------------
    # def action_hub_receive(self):
    #     for manifest in self:

    #         # 1. State validation
    #         if manifest.state != "confirmed":
    #             raise UserError("Only confirmed manifests can be received at hub.")

    #         if not manifest.destination_location_id:
    #             raise UserError("Destination hub is not set on this manifest.")

    #         # if not manifest.good_line_ids:
    #         #     raise UserError("No goods found in this manifest.")

    #         # 2. Create Hub Inward Ledger
    #         self.env["transport.hub.inventory"].update_hub_inventory(
    #             movement_type="in",
    #             hub_id=manifest.destination_location_id.id,
    #             booking_id=manifest.manifest_good_line_ids.booking_id.id,
    #             manifest_id=manifest.id,
    #             goods_line_ids=manifest.manifest_good_line_ids,
    #             source_location_id=manifest.source_location_id.id,
    #             destination_location_id=manifest.destination_location_id.id,
    #             remarks=f"Manifest {manifest.name} received at hub",
    #         )

    #         # 3. Mark manifest as arrived
    #         manifest.state = "received"

    def action_hub_receive(self):
        self.ensure_one()

        if not self.manifest_good_line_ids:
            raise UserError("No goods found in this manifest.")
        if not self.destination_location_id:
            raise UserError("Destination hub is not set on this manifest.")

        return {
            "name": "Hub Receive",
            "type": "ir.actions.act_window",
            "res_model": "transport.hub.receive.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_manifest_id": self.id,
                "default_booking_id": self.manifest_good_line_ids.booking_id.id,
                "default_receiving_hub_id": self.destination_location_id.id,
                "default_vehicle_id": self.vehicle_id.id,
                "default_driver_id": self.driver_id.id,
            },
        }

    def action_confirm(self):
        for manifest in self:

            if manifest.state != "draft":
                continue

            if not manifest.vehicle_id:
                raise ValidationError("Please assign a vehicle.")

            if not manifest.driver_id:
                raise ValidationError("Please assign a driver.")

            if not manifest.leg_ids:
                raise ValidationError("Manifest must contain at least one leg.")

            # 🔒 Lock legs
            manifest.leg_ids.write({"state": "assigned"})
            manifest.state = "confirmed"

            # Make movement in transit
            movements = self.movement_leg_id.movement_id
            movements.write({"state": "in_transit"})
