from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import pdb
import logging

_logger = logging.getLogger(__name__)


class TransportHubInventory(models.Model):
    _name = "transport.hub.inventory"
    _description = "Hub Goods Inventory (Ledger)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        default=lambda self: self.env["ir.sequence"].next_by_code(
            "transport.hub.inventory"
        ),
    )

    date = fields.Datetime(
        string="Date",
        default=fields.Datetime.now,
        required=True,
    )

    hub_id = fields.Many2one(
        "transport.location",
        string="Hub",
        required=True,
        domain="[('owner_type','=','own')]",
        index=True,
    )

    inventory_line_ids = fields.One2many(
        "transport.hub.inventory.line",
        "inventory_id",
        string="Delivery Goods Lines",
        tracking=True,
    )

    movement_type = fields.Selection(
        [
            ("in", "Inward"),
            ("out", "Outward"),
        ],
        required=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("valid", "Valid"),
            ("received", "Received"),
            ("assigned", "Assigned"),
            ("partial", "Partial Delivered"),
            ("delivered", "Full Delivered"),
            ("failed", "Failed"),
            ("declined", "Declined"),
            ("cancelled", "Cancelled"),
        ],
        default="received",
    )

    manifest_id = fields.Many2one(
        "transport.manifest",
        string="Manifest",
        index=True,
        ondelete="restrict",
    )

    current_leg_id = fields.Many2one(
        related="manifest_id.movement_leg_id",
        string="Current Leg",
        store=True,
        index=True,
    )
    manifest_good_line_id = fields.Many2one(
        "transport.manifest.good.line",
        string="Manifest Good Line",
        required=True,
        ondelete="restrict",
        index=True,
    )
    good_line_id = fields.Many2one(
        "transport.goods.line",
        string="Goods Line",
        required=True,
    )

    booking_id = fields.Many2one(
        "transport.booking",
        string="Booking",
        index=True,
        ondelete="restrict",
    )

    source_location_id = fields.Many2one(
        "transport.location",
        string="Source",
    )

    destination_location_id = fields.Many2one(
        "transport.location",
        string="Destination",
    )

    qty_loaded = fields.Float(string="Quantity Loaded", default="0.00")
    qty_received = fields.Float(string="Quantity Received", default="0.00")
    qty_instock = fields.Float(
        string="Quantity Instock",
        compute="_compute_qty_instock",
        readonly=True,
    )

    remarks = fields.Char()

    # == For deliver
    delivery_created = fields.Boolean(
        string="Is  delivery created",
        default=False,
    )

    # == View Purpose
    next_leg_id = fields.Many2one(
        "transport.movement.leg",
        string="Next Leg",
        compute="_compute_next_leg",
        store=True,
        readonly=True,
    )

    next_leg_type = fields.Selection(
        related="next_leg_id.leg_type",
        string="Leg Type",
        readonly=True,
        store=False,
    )

    next_destination_id = fields.Many2one(
        "transport.location",
        string="Next Destination",
        compute="_compute_next_destination",
        readonly=True,
        store=False,
    )

    vehicle_id = fields.Many2one(
        related="manifest_id.vehicle_id",
        string="Vehicle",
        store=False,
    )

    driver_id = fields.Many2one(
        related="manifest_id.driver_id",
        string="Driver",
        store=False,
        readonly=True,
    )

    good_type_id = fields.Many2one(
        related="manifest_good_line_id.goods_type_id",  # adjust based on your model
        string="Good Type",
        store=False,
        readonly=True,
    )

    good_description = fields.Char(
        related="manifest_good_line_id.description",  # adjust based on your model
        string="Description",
        store=False,
        readonly=True,
    )

    good_status = fields.Selection(
        related="manifest_good_line_id.status",
        string="Received Status",
        readonly=True,
        store=False,
    )

    docket_no = fields.Char(
        related="manifest_good_line_id.docket_no",  # adjust based on your model
        string="Docket No",
        store=False,
        readonly=True,
    )

    @api.depends(
        "inventory_line_ids.movement_type", "inventory_line_ids.movement_quantity"
    )
    def _compute_qty_instock(self):
        """
        Compute available stock quantity.

        Formula:
            qty_instock = sum(inward qty) - sum(outward qty)

        Triggered When:
            - Movement line added
            - Movement quantity changed
            - Movement type changed
        """
        for rec in self:
            qty = 0.0
            for line in rec.inventory_line_ids:
                if line.movement_type == "in":
                    qty += line.movement_quantity
                elif line.movement_type == "out":
                    qty -= line.movement_quantity

            rec.qty_instock = qty

    @api.depends(
        "manifest_id",
        "manifest_id.movement_leg_id",
        "manifest_id.movement_leg_id.sequence",
    )
    def _compute_next_leg(self):
        for rec in self:
            rec.next_leg_id = False

            if not rec.manifest_id or not rec.manifest_id.movement_leg_id:
                continue

            current_leg = rec.manifest_id.movement_leg_id
            movement = current_leg.movement_id

            next_leg = self.env["transport.movement.leg"].search(
                [
                    ("movement_id", "=", movement.id),
                    ("sequence", ">", current_leg.sequence),
                ],
                order="sequence asc",
                limit=1,
            )

            rec.next_leg_id = next_leg

    @api.depends("next_leg_id")
    def _compute_next_destination(self):
        for rec in self:
            rec.next_destination_id = (
                rec.next_leg_id.to_location_id if rec.next_leg_id else False
            )

    def action_receive_confirm(self):

        for rec in self:
            if rec.state != "valid":
                raise UserError("Only Valid inventory can be confirmed.")

            if not rec.current_leg_id:
                raise UserError("Current movement leg is missing.")

            leg = rec.current_leg_id
            qty = rec.qty_received
            good_line_id = rec.manifest_good_line_id.good_line_id.id
            inventory_line_model = self.env["transport.hub.inventory.line"]

            from_loc = leg.from_location_id
            to_loc = leg.to_location_id

            # -------------------------------
            # 1️⃣ OUT from source HUB (if HUB)
            # -------------------------------
            if from_loc and from_loc.owner_type == "own":
                source_inventory = self.env["transport.hub.inventory"].search(
                    [("hub_id", "=", from_loc.id)],
                    limit=1,
                )

                if not source_inventory:
                    raise UserError(f"No inventory found for hub {from_loc.name}")

                inventory_line_model.create(
                    {
                        "inventory_id": source_inventory.id,
                        "movement_type": "out",
                        "good_line_id": good_line_id,
                        "movement_quantity": qty,
                        "description": (
                            f"Moved out from {from_loc.name} "
                            f"to {to_loc.name} "
                            f"via {rec.manifest_id.name}"
                        ),
                    }
                )

                # picking = self._action_stock_move(
                #     source_location_id=rec.current_leg_id.from_location_id.inventory_location_id.id,
                #     destination_location_id=rec.current_leg_id.to_location_id.inventory_location_id.id,
                #     unit_id=uom.id,
                #     product_id=product.id,
                #     qty_received=rec.qty_received,
                # )
                # rec.picking_id = picking.id

            # -------------------------------
            # 2️⃣ IN to destination HUB (if HUB)
            # -------------------------------
            if to_loc and to_loc.owner_type == "own":
                destination_inventory = self.env["transport.hub.inventory"].search(
                    [("hub_id", "=", to_loc.id)],
                    limit=1,
                )

                if not destination_inventory:
                    raise UserError(f"No inventory found for hub {to_loc.name}")

                inventory_line_model.create(
                    {
                        "inventory_id": destination_inventory.id,
                        "movement_type": "in",
                        "good_line_id": good_line_id,
                        "movement_quantity": qty,
                        "description": (
                            f"Received at {to_loc.name} "
                            f"from {from_loc.name if from_loc else 'Customer'} "
                            f"via {rec.manifest_id.name}"
                        ),
                    }
                )

                # self._action_stock_move(
                #     source_location_id=rec.current_leg_id.from_location_id.inventory_location_id.id,
                #     destination_location_id=rec.current_leg_id.to_location_id.inventory_location_id.id,
                #     unit_id=uom.id,
                #     product_id=product.id,
                #     qty_received=rec.qty_received,
                # )

            # -------------------------------
            # 3️⃣ Mark inventory received
            # -------------------------------
            rec.state = "received"


# ----------------------
# Hub Inventory line
# ----------------------
class TransportHubInventoryLine(models.Model):
    _name = "transport.hub.inventory.line"
    _description = "Transport Inventory Line"

    date = fields.Datetime(
        string="Date",
        default=fields.Datetime.now,
        required=True,
    )
    inventory_id = fields.Many2one(
        "transport.hub.inventory",
        string="Inventory Id",
        required=True,
        ondelete="cascade",
    )
    stock_move_id = fields.Many2one(
        "stock.move",
        copy=False,
        string="Stock Move",
        ondelete="set null",
    )
    # picking_id = fields.Many2one("stock.picking", string="Stock Picking", copy=False)
    movement_type = fields.Selection(
        [
            ("in", "Inward"),
            ("out", "Outward"),
        ],
        required=True,
        index=True,
    )
    good_line_id = fields.Many2one(
        "transport.goods.line",
        string="Goods Line",
        required=True,
        readonly=True,
    )
    movement_quantity = fields.Float(string="Movement Quantity", required="1")
    description = fields.Char(string="Description", required="1")

    # Store false fileds
    good_type_id = fields.Many2one(
        "transport.goods.type",
        related="good_line_id.goods_type_id",  # adjust based on your model
        string="Good Type",
        store=False,
        readonly=True,
    )
    good_description = fields.Char(
        related="good_line_id.description",  # adjust based on your model
        string="Good Description",
        store=False,
        readonly=True,
    )
