from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare
import logging

_logger = logging.getLogger(__name__)


class TransportHubReceiveWizard(models.TransientModel):
    _name = "transport.hub.receive.wizard"
    _description = "Hub Receive Wizard"

    manifest_id = fields.Many2one("transport.manifest", readonly=True, required=True)
    booking_id = fields.Many2one("transport.booking", readonly=True)
    leg_id = fields.Many2one("transport.movement.leg", readonly=True)
    vehicle_id = fields.Many2one("fleet.vehicle", readonly=True)
    driver_id = fields.Many2one("res.partner", readonly=True)

    receiving_hub_id = fields.Many2one(
        "transport.location",
        string="Receiving Hub",
        readonly=True,
    )

    receive_line_ids = fields.One2many(
        "transport.hub.receive.line.wizard",
        "wizard_id",
        string="Goods",
    )

    remarks = fields.Text()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        manifest_id = self.env.context.get("default_manifest_id")
        if manifest_id:
            manifest = self.env["transport.manifest"].browse(manifest_id)

            lines = []
            for manifest_good_line in manifest.manifest_good_line_ids:
                lines.append(
                    (
                        0,
                        0,
                        {
                            "manifest_good_line_id": manifest_good_line.id,
                            "qty_loaded": manifest_good_line.qty_loaded,
                            "qty_received": manifest_good_line.qty_loaded,  # default
                        },
                    )
                )

            res["receive_line_ids"] = lines
            _logger.warning("========================%s", lines)

        return res

    def action_confirm_receive(self):
        self.ensure_one()
        if not self.receive_line_ids:
            raise UserError("No goods to receive.")

        inventory_model = self.env["transport.hub.inventory"]

        # -----------------------------
        # Process each received line
        # -----------------------------
        for line in self.receive_line_ids:

            # -----------------------------
            # Validation
            # -----------------------------
            if line.receive_status != "rejected" and line.qty_received <= 0:
                raise UserError(
                    f"Received quantity must be greater than zero for goods: {line.manifest_good_line_id.name}"
                )

            if (
                float_compare(
                    line.qty_received,
                    line.qty_loaded,
                    precision_digits=6,
                )
                > 0
            ):
                raise UserError(
                    f"Received quantity cannot exceed loaded quantity for goods: {line.manifest_good_line_id.name}"
                )

            # -----------------------------
            # Rejected Goods
            # -----------------------------
            if line.receive_status == "rejected":
                if not line.rejection_reason:
                    raise UserError(
                        f"Please enter rejection reason for goods: {line.manifest_good_line_id.name}"
                    )
                line.manifest_good_line_id.status = "rejected"
                continue

            # -----------------------------
            # Accept Full / Partial Goods
            # -----------------------------
            inventory_model.create(
                {
                    "hub_id": self.receiving_hub_id.id,
                    # "movement_leg_id": self.leg_id,
                    "movement_type": "in",
                    "booking_id": self.booking_id.id,
                    "manifest_id": self.manifest_id.id,
                    "manifest_good_line_id": line.manifest_good_line_id.id,
                    "good_line_id": line.manifest_good_line_id.good_line_id.id,
                    "source_location_id": self.manifest_id.source_location_id.id,
                    "destination_location_id": self.receiving_hub_id.id,
                    "qty_loaded": line.qty_loaded,
                    "qty_received": line.qty_received,
                    "remarks": self.remarks,
                    "state": "valid",
                }
            )

            # Update manifest good status
            if line.receive_status == "full":
                line.manifest_good_line_id.status = "full"
            elif line.receive_status == "partial":
                line.manifest_good_line_id.status = "partial"

        # -----------------------------
        # Update Manifest State
        # -----------------------------
        received_count = len(
            self.receive_line_ids.filtered(
                lambda l: l.receive_status in ("full", "partial")
            )
        )

        if received_count:
            self.manifest_id.state = "receivable"
        else:
            self.manifest_id.state = "rejected"

        return {"type": "ir.actions.act_window_close"}


# -----------------------
class TransportHubReceiveLineWizard(models.TransientModel):
    _name = "transport.hub.receive.line.wizard"
    _description = "Hub Receive Line"

    wizard_id = fields.Many2one(
        "transport.hub.receive.wizard",
        required=True,
        ondelete="cascade",
    )
    manifest_good_line_id = fields.Many2one(
        "transport.manifest.good.line",
        string="Manifest Good Line",
        required=True,
    )
    good_line_id = fields.Many2one(
        "transport.good.line",
        related="manifest_good_line_id.good_line_id",
        string="Goods",
        readonly=True,
    )

    # 🔹 Extra info (RELATED)
    good_type_id = fields.Many2one(related="manifest_good_line_id.goods_type_id")
    docket_no = fields.Char(related="manifest_good_line_id.docket_no")
    goods_description = fields.Char(related="manifest_good_line_id.description")

    qty_loaded = fields.Float(string="Loaded Qty")
    qty_received = fields.Float(string="Received Qty", required=True)

    receive_status = fields.Selection(
        [
            ("full", "Fully Received"),
            ("partial", "Partially Received"),
            ("rejected", "Rejected"),
        ],
        required=True,
        default="full",
    )
    rejection_reason = fields.Text()
