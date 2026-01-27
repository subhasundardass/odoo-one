from odoo import models, fields, api, Command
from odoo.exceptions import ValidationError, UserError
import pdb
import logging

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Delivery Leg (Final Movement Leg)
# ---------------------------------------------------------
class TransportGoodDelivery(models.Model):
    _name = "transport.good.delivery"
    _description = "Transport Delivery"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Delivery Reference",
        required=True,
        copy=False,
        default=lambda self: self.env["ir.sequence"].next_by_code(
            "transport.good.delivery"
        ),
    )

    hub_inventory_id = fields.Many2one(
        "transport.hub.inventory",
        string="Hub Inventory",
        required=True,
        ondelete="restrict",
        index=True,
    )

    movement_leg_id = fields.Many2one(
        "transport.movement.leg",
        string="Movement Leg",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    hub_id = fields.Many2one(
        "transport.location",
        string="Hub",
        required=True,
        tracking=True,
    )

    delivery_date = fields.Date(string="Delivery Date", tracking=True)

    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehicle",
        tracking=True,
    )

    driver_id = fields.Many2one(
        "res.partner",
        string="Driver",
        domain="[('partner_type', '=', 'driver')]",
        tracking=True,
    )

    state = fields.Selection(
        [
            ("assigned", "Assigned"),
            ("confirmed", "Confirmed"),
            ("out_for_delivery", "Out for Delivery"),
            ("partial", "Partially Delivered"),
            ("done", "Completed"),
            ("failed", "Failed"),
        ],
        default="assigned",
        tracking=True,
    )

    # ------------------------
    # Delivery Line relation
    # ------------------------
    delivery_line_ids = fields.One2many(
        "transport.good.delivery.line",
        "delivery_id",
        string="Delivery Goods Lines",
    )

    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        readonly=True,
        copy=False,
        domain="[('move_type', '=', 'out_invoice')]",
    )
    # ------------------------
    # POD relation
    # ------------------------
    pod_ids = fields.One2many(
        "transport.good.delivery.pod",
        "delivery_id",
        string="Proof of Delivery",
    )

    # ----------------------------
    # Computations
    # ----------------------------
    @api.depends("delivery_line_ids.expected_qty", "delivery_line_ids.delivered_qty")
    def _compute_totals(self):
        for rec in self:
            rec.total_expected_qty = sum(
                line.expected_qty for line in rec.delivery_line_ids
            )
            rec.total_delivered_qty = sum(
                line.delivered_qty for line in rec.delivery_line_ids
            )

    # ----------------------------
    # Actions
    # ----------------------------
    def action_confirm(self):
        for rec in self:
            if not rec.delivery_line_ids:
                raise ValidationError("No delivery goods found.")

            rec.state = "confirmed"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_assign(self):
        for rec in self:
            if not rec.vehicle_id or not rec.driver_id:
                raise ValidationError("Vehicle and Driver must be assigned.")
            rec.state = "assigned"

    def action_start_delivery(self):
        for rec in self:
            if rec.state != "confirmed":
                raise ValidationError("Delivery must be confirmed first.")

            if not rec.delivery_line_ids:
                raise ValidationError("No delivery goods found.")

            rec.state = "out_for_delivery"

    def action_mark_deliverd(self):

        for rec in self:
            if not rec.delivery_line_ids:
                raise ValidationError("No delivery goods found.")

            pod_exists = self.env["transport.good.delivery.pod"].search(
                [("delivery_id", "=", rec.id)], limit=1
            )
            if not pod_exists:
                raise ValidationError("Proof of Delivery is required.")

            # 🚨 NEW VALIDATION: Delivered qty must be > 0
            zero_qty_lines = rec.delivery_line_ids.filtered(
                lambda l: l.delivered_qty <= 0
            )
            if zero_qty_lines:
                raise ValidationError(
                    "Delivered quantity must be greater than zero for all delivery lines."
                )

            # ---- LINE STATE UPDATE ----
            all_done = True
            for line in rec.delivery_line_ids:
                if line.delivered_qty < line.expected_qty:
                    line.state = "partial"
                    # self._update_inventory_status(strState="partial")
                    all_done = False
                else:
                    line.state = "delivered"
                    # self._update_inventory_status(strState="delivered")

                ## Create outward inventory
                # self._create_inventory_line_outward(
                #     good_line_id=line.good_line_id, qty_received=line.delivered_qty
                # )
                ## Update Delived Status
                # self._update_inventory_status(delivered_qty=line.delivered_qty)

            ## ---- HEADER STATE UPDATE ----
            # rec.state = "done" if all_done else "partial"

            # 3 -- lock Booking
            # 3 -- lock Stock Movement
            # 5 -- create Invoice
            invoice = self._create_invoice()
            # self.invoice_id = invoice.id

    def action_fail(self):
        for rec in self:
            rec.state = "failed"

    # Create outward inventory movement entries for delivered goods.

    def _create_inventory_line_outward(self, good_line_id, qty_received):

        # StockMove = self.env["stock.move"]
        Inventory_line_model = self.env["transport.hub.inventory.line"]
        # Picking = self.env["stock.picking"]

        good_line = self.env["transport.goods.line"].browse(good_line_id.id)
        product = good_line.product_id

        if not product:
            raise ValidationError("Product not defined on Goods Line.")

        # location_src_id = self.hub_inventory_id.source_location_id.id
        # location_dest_id = self.hub_inventory_id.destination_location_id.id
        # uom = good_line.unit_id or product.uom_id

        # picking = Picking.create(
        #     {
        #         "picking_type_id": self.env.ref("stock.picking_type_out").id,
        #         "location_id": location_src_id,
        #         "location_dest_id": location_dest_id,
        #         "origin": self.name,
        #     }
        # )

        # 1️⃣ Create stock move
        # move_out = StockMove.create(
        #     {
        #         "name": f"Delivery {self.name}",
        #         "product_id": product.id,
        #         "product_uom_qty": qty_received,
        #         "product_uom": uom.id,
        #         "location_id": location_src_id,
        #         "location_dest_id": location_dest_id,
        #         "picking_id": picking.id,
        #     }
        # )
        # move_out._action_confirm()
        # move_out._action_assign()
        # move_out._action_done()

        Inventory_line_model.create(
            {
                "inventory_id": self.hub_inventory_id.id,
                "movement_type": "out",
                "good_line_id": good_line_id.id,
                "movement_quantity": qty_received,
                "description": f"Delivered Goods by {self.name}",
            }
        )

    # Update Inventory Status
    def _update_inventory_status(self, delivered_qty):
        for rec in self:
            hub_inventory = rec.hub_inventory_id
            if not hub_inventory:
                continue

            received_qty = hub_inventory.qty_received or 0.0

            if delivered_qty < received_qty:
                state = "partial"
            else:
                state = "delivered"

            hub_inventory.write({"state": state})

    # Lock the related booking record.
    def _lock_booking(self):
        """
        Lock the related booking record.

        Purpose:
        - Prevent any further modification after delivery completion
        - Ensure data consistency between booking and delivery

        Triggered When:
        - Delivery is marked as Partial or Done
        """
        for rec in self:
            if rec.booking_id:
                rec.booking_id.write({"is_locked": True})

    # Lock the related stock movement record.
    def _lock_stock_movement(self):
        """
        Lock the related stock movement record.

        Purpose:
        - Prevent stock quantity manipulation after delivery
        - Maintain inventory audit integrity

        Triggered When:
        - Delivery is marked as Partial or Done
        """
        for rec in self:
            if rec.stock_move_id:
                rec.stock_move_id.write({"is_locked": True})

    # Generate customer invoice based on delivered quantities.
    def _create_invoice(self):
        AccountMove = self.env["account.move"]

        for rec in self:
            if rec.invoice_id:
                continue

            partner = rec.hub_inventory_id.manifest_id.movement_id.booking_id.partner_id
            if not partner:
                raise UserError("Customer not found for delivery")

            # Get B2B rate
            rate_data = self.env["transport.b2b.rate"].get_applicable_b2b_rate(
                party_id=None,
                uom_id=self.env.ref("uom.product_uom_kgm").id,
            )
            rate = rate_data.get("rate", 0.0)
            if rate <= 0:
                raise UserError("Invalid B2B rate")

            invoice_lines = []

            for line in rec.delivery_line_ids.filtered(lambda l: l.delivered_qty > 0):
                product = line.good_line_id.product_id

                # Income account from Chart of Accounts (standard Odoo way)
                account = (
                    product.property_account_income_id
                    or product.categ_id.property_account_income_categ_id
                )

                if not account:
                    raise UserError(
                        f"No income account defined for product {product.display_name}"
                    )

                charged_weight = line.good_line_id.charged_weight
                if charged_weight <= 0:
                    raise UserError("Charged weight must be greater than zero")

                invoice_lines.append(
                    {
                        "product_id": product.id,
                        "name": product.display_name,
                        "quantity": charged_weight,  # ✅ weight-based quantity
                        "price_unit": rate,
                        "account_id": account.id,
                    }
                )

            if not invoice_lines:
                raise UserError("No invoiceable lines found")

            invoice = AccountMove.create_invoice(
                partner_id=partner.id,
                move_type="out_invoice",
                ref=f"Delivery {rec.name}",
                lines=invoice_lines,
            )

            rec.invoice_id = invoice.id

        return True

    # Prevent modification of delivery records after completion.
    @api.constrains("state")
    def _check_edit_after_delivery(self):
        """
        Prevent modification of delivery records after completion.

        Purpose:
        - Maintain audit trail
        - Avoid accidental data corruption

        Restriction:
        - Records in 'partial' or 'done' state are locked
        """
        for rec in self:
            if rec.state in ("partial", "done"):
                # raise ValidationError("Delivered records cannot be modified.")
                pass

    # -----------------------------------------------------


# ---------------------------------------------------------
# Delivery Goods Line
# ---------------------------------------------------------
class TransportDeliveryLine(models.Model):
    _name = "transport.good.delivery.line"
    _description = "Transport Delivery Goods Line"

    delivery_id = fields.Many2one(
        "transport.good.delivery",
        string="Delivery Id",
        required=True,
        index=True,
        ondelete="cascade",
    )

    good_line_id = fields.Many2one(
        "transport.goods.line",
        string="Goods Line",
        required=True,
        readonly=True,
        store=True,
    )

    expected_qty = fields.Float(string="Expected Qty", required=True)
    loaded_qty = fields.Float(string="Loaded Qty")
    delivered_qty = fields.Float(string="Delivered Qty")
    short_qty = fields.Float(string="Short Qty")
    rejected_qty = fields.Float(string="Rejected Qty")

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("delivered", "Delivered"),
            ("partial", "Partial"),
            ("failed", "Failed"),
        ],
        default="pending",
    )

    @api.onchange("delivered_qty")
    def _onchange_delivered_qty(self):
        for rec in self:
            if rec.delivered_qty > rec.expected_qty:
                raise ValidationError(
                    "Delivered quantity cannot exceed expected quantity."
                )

            if rec.delivered_qty == rec.expected_qty:
                rec.state = "delivered"
            elif rec.delivered_qty > 0:
                rec.state = "partial"
            else:
                rec.state = "pending"


# ---------------------------------------------------------
# Proof of Delivery (POD)
# ---------------------------------------------------------
class TransportDeliveryPOD(models.Model):
    _name = "transport.good.delivery.pod"
    _description = "Transport Proof of Delivery"
    _order = "delivered_at desc"

    delivery_id = fields.Many2one(
        "transport.good.delivery",
        string="Delivery",
        required=True,
        ondelete="cascade",
        index=True,
    )

    pod_type = fields.Selection(
        [
            ("signature", "Signature"),
            ("otp", "OTP"),
            ("photo", "Photo"),
        ],
        string="POD Type",
        required=True,
        index=True,
    )

    signed_by = fields.Char(string="Signed By")
    otp = fields.Char(string="OTP")
    otp_varified = fields.Boolean(string="OTP Verified", default=False)

    # Real delivery often has multiple photos
    attachment_ids = fields.Many2many("ir.attachment", string="POD Attachments")

    delivered_at = fields.Datetime(
        string="Delivered At",
        default=fields.Datetime.now,
        required=True,
    )

    latitude = fields.Float(string="Latitude")
    longitude = fields.Float(string="Longitude")

    _sql_constraints = [
        (
            "unique_pod_per_type",
            "unique(delivery_id, pod_type)",
            "Only one POD of each type is allowed per delivery.",
        )
    ]
