from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import pdb
import logging

_logger = logging.getLogger(__name__)


class TransportDeliveryWizard(models.TransientModel):
    _name = "transport.good.delivery.wizard"
    _description = "Wizard to assign Vehicle, Driver, and Delivery Location"

    # ------------------------
    # Reference to Hub Inventory
    # ------------------------
    hub_inventory_id = fields.Many2one(
        "transport.hub.inventory",
        string="Hub Inventory",
        required=True,
    )

    hub_id = fields.Many2one(
        related="hub_inventory_id.hub_id",
        string="Hub",
        store=True,
        readonly=True,
    )

    received_quantity = fields.Float()
    expected_quantity = fields.Float()
    # good_line_id = fields.Many2one(
    #     "transport.good.line",
    #     string="Goods Line",
    #     required=True,
    # )

    # ------------------------
    # Fields for Delivery
    # ------------------------
    movement_leg_id = fields.Many2one(
        "transport.movement.leg",
        string="Last-Mile Leg",
        required=True,
    )

    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehicle",
        required=True,
    )

    driver_id = fields.Many2one(
        "res.partner",
        string="Driver",
        domain="[('partner_type', '=', 'driver')]",
        required=True,
    )

    destination_location_id = fields.Many2one(
        "stock.location",
        string="Delivery Location",
        required=True,
    )

    delivery_date = fields.Date(
        string="Delivery Date",
        default=fields.Date.today,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("assigned", "Assigned"),
            ("out", "Out for Delivery"),
            ("done", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
    )

    # ------------------------
    # Default Destination
    # ------------------------
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        hub_inventory_id = self.env.context.get("default_hub_inventory_id")

        if hub_inventory_id:
            hub_inventory = self.env["transport.hub.inventory"].browse(hub_inventory_id)
            current_leg = hub_inventory.manifest_id.movement_leg_id

            # set
            res["received_quantity"] = hub_inventory.qty_received
            res["expected_quantity"] = hub_inventory.qty_received

            if not current_leg:
                raise UserError("Current movement leg not found in manifest.")

            movement = current_leg.movement_id

            # Find next leg in sequence
            next_leg = self.env["transport.movement.leg"].search(
                [
                    ("movement_id", "=", movement.id),
                    ("sequence", ">", current_leg.sequence),
                ],
                order="sequence asc",
                limit=1,
            )
            if next_leg and next_leg.leg_type != "lastmile":
                raise UserError(
                    "Delivery can only be created for the Last-Mile leg.\n"
                    "This shipment must move via Manifest."
                )
            if next_leg:
                res["movement_leg_id"] = next_leg.id
                res["destination_location_id"] = next_leg.to_location_id.id
            else:
                res["movement_leg_id"] = False
                res["destination_location_id"] = False

        return res

    # ------------------------
    # Confirm Assignment Action
    # ------------------------
    def action_assign_delivery(self):
        self.ensure_one()
        hub = self.hub_inventory_id

        # Validation checks
        if not hub:
            raise ValidationError("Hub inventory not found.")

        if hub.delivery_created:
            raise ValidationError("Delivery already created for this inventory.")

        if hub.state != "received":
            raise ValidationError("Hub inventory must be received to create delivery.")

        if not hub.next_leg_id:
            raise ValidationError("No last-mile leg found for delivery.")

        if not hub.hub_id:
            raise ValidationError("Hub is missing in hub inventory.")

        # Create Delivery Leg
        delivery = self.env["transport.good.delivery"].create(
            {
                "movement_leg_id": hub.next_leg_id.id,
                "hub_inventory_id": self.hub_inventory_id.id,
                "hub_id": hub.hub_id.id,
                "delivery_date": self.delivery_date,
                "vehicle_id": self.vehicle_id.id,
                "driver_id": self.driver_id.id,
                "state": "assigned",  # Assigned directly from wizard
            }
        )

        # delete delivery_line if already exist for delivery_id

        # --------------------
        # Create Delivery Lines (IMPORTANT FIX)
        # --------------------
        for inv_line in hub.inventory_line_ids.filtered(
            lambda l: l.movement_quantity > 0
        ):
            self.env["transport.good.delivery.line"].create(
                {
                    "delivery_id": delivery.id,
                    "good_line_id": inv_line.good_line_id.id,
                    "expected_qty": self.expected_quantity,
                }
            )
        # Mark Hub Inventory as having delivery created
        hub.write(
            {
                "delivery_created": True,
                "state": "assigned",
            }
        )

        # Open the newly created Delivery Leg form

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Success",
                "message": f"Delivery {delivery.name} created",
                "type": "success",
                "next": {
                    "type": "ir.actions.act_window_close",
                },
            },
        }
