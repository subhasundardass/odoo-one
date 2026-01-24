from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, time
import json
import logging

_logger = logging.getLogger(__name__)


class TransportAssignManifestWizard(models.TransientModel):
    _name = "transport.assign.manifest.wizard"
    _description = "Assign Movement Leg to Manifest"

    leg_ids = fields.Many2many(
        "transport.movement.leg",
        string="Movement Legs",
        required=True,
    )

    good_line_ids = fields.One2many(
        "transport.assign.manifest.line.wizard", "wizard_id", string="Goods to Load"
    )

    manifest_id = fields.Many2one(
        "transport.manifest",
        # required=True,
        domain=[("state", "in", ("draft", "confirmed"))],
        placeholder="Leave empty to create / reuse manifest",
    )

    # Execution inputs (stored on Manifest)
    vehicle_id = fields.Many2one("fleet.vehicle", required=True)
    driver_id = fields.Many2one(
        "res.partner",
        string="Driver",
        required=True,
        domain="[('partner_type','=', 'driver')]",
        context={"default_partner_type": "driver"},
    )

    from_location_id = fields.Many2one(
        "transport.location",
        required=True,
    )
    to_location_id = fields.Many2one(
        "transport.location",
        required=True,
    )

    departure_datetime = fields.Datetime(required=True)
    expected_arrival_datetime = fields.Datetime(string="Expected Arrival")
    estimated_cost = fields.Float()

    # temporary solution
    goods_snapshot_json = fields.Text(string="Goods Snapshot", readonly=True)

    def action_assign_to_manifest(self):
        self.ensure_one()
        booking_id = self.env.context.get("booking_id")
        movement_leg_id = self.env.context.get("movement_leg_id")
        from_location_id = self.env.context.get("default_from_location_id")
        to_location_id = self.env.context.get("default_to_location_id")
        goods_data = json.loads(self.goods_snapshot_json or "[]")

        if not self.leg_ids:
            raise ValidationError("No legs selected.")

        if self.manifest_id:
            manifest = self.manifest_id
        else:

            manifest = self.env["transport.manifest"].create(
                {
                    "movement_leg_id": movement_leg_id,
                    "vehicle_id": self.vehicle_id.id,
                    "driver_id": self.driver_id.id,
                    "source_location_id": self.from_location_id.id,
                    "destination_location_id": self.to_location_id.id,
                    "departure_time": self.departure_datetime,
                    "arrival_time": self.expected_arrival_datetime,
                    "estimated_cost": self.estimated_cost,
                }
            )

        # -----------------------------
        # 2️⃣ Assign legs
        # -----------------------------
        manifest.leg_ids = [(4, leg.id) for leg in self.leg_ids]

        # -----------------------------
        # 3️⃣ Remove old manifest goods
        # -----------------------------
        self.env["transport.manifest.good.line"].search(
            [
                ("manifest_id", "=", manifest.id),
                ("booking_id", "=", booking_id),
                ("movement_leg_id", "=", movement_leg_id),
            ]
        ).unlink()

        # -----------------------------
        # 4️⃣ Create / Update manifest good lines
        # -----------------------------
        idx = 0

        for line in self.good_line_ids.filtered(lambda l: l.load_qty > 0):

            good = goods_data[idx]

            # 🔍 Check if this good already exists in manifest
            vals = {
                "manifest_id": manifest.id,
                "movement_leg_id": movement_leg_id,
                "booking_id": booking_id,
                "good_line_id": good["booking_good_line_id"],
                "docket_no": good["docket_no"],
                "goods_type_id": good["goods_type_id"],
                "unit": good["unit_id"],
                "qty_loaded": line.load_qty,  # ✅ USER ENTERED VALUE
                "from_location_id": from_location_id,
                "to_location_id": to_location_id,
            }
            # _logger.info("EXISTING---------%s", existing_line)
            # if existing_line:
            #     # ♻️ Update instead of duplicate
            #     continue
            # else:
            # ➕ Create new
            self.env["transport.manifest.good.line"].create(vals)
            idx += 1
        # Update movement_leg
        movement_leg = self.env["transport.movement.leg"].browse(movement_leg_id)
        movement_leg.write(
            {
                "state": "assigned",  # or "in_transit" depending on your workflow
                "manifest_id": manifest.id,
            }
        )
        return {"type": "ir.actions.act_window_close"}

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        leg_ids_ctx = self.env.context.get("default_leg_ids")
        leg_ids = []

        if leg_ids_ctx:
            # M2M command format
            if (
                isinstance(leg_ids_ctx, list)
                and leg_ids_ctx
                and isinstance(leg_ids_ctx[0], (list, tuple))
            ):
                for cmd in leg_ids_ctx:
                    if cmd[0] == 6:  # set
                        leg_ids.extend(cmd[2])
                    elif cmd[0] == 4:  # add
                        leg_ids.append(cmd[1])
            else:
                leg_ids = leg_ids_ctx

        # Make sure we have valid leg IDs
        legs = self.env["transport.movement.leg"].browse(leg_ids)
        if not legs:
            return res  # no legs provided

        # Validate leg states
        if any(l.state != "planned" for l in legs):
            raise ValidationError("Only planned legs can be assigned to a manifest.")

        # Set header fields
        res.update(
            {
                "leg_ids": [(6, 0, legs.ids)],  # correctly assign M2M
                "from_location_id": legs[0].from_location_id.id,
                "to_location_id": legs[0].to_location_id.id,
            }
        )

        # Populate wizard lines
        lines = []
        good_data_line = []
        for leg in legs:
            movement = leg.movement_id
            booking = movement.booking_id  # single booking
            if not booking:
                continue

            for good in booking.goods_line_ids:
                lines.append(
                    (
                        0,
                        0,
                        {
                            "movement_leg_id": leg.id,  # assign leg here!
                            "booking_id": booking.id,
                            "docket_no": booking.docket_no,
                            "booking_good_line_id": good.id,
                            "goods_type_id": good.goods_type_id.id or False,
                            "weight": good.actual_weight or 0.0,
                            "unit_id": good.unit_id.id or False,
                            "available_qty": good.qty or 0.0,
                            "load_qty": 0.0,
                        },
                    )
                )
                good_data_line.append(
                    {
                        "booking_id": booking.id,  # ✅ MUST ADD
                        "booking_good_line_id": good.id,
                        "docket_no": booking.docket_no,
                        "goods_type_id": good.goods_type_id.id,
                        "unit_id": good.unit_id.id,
                        "available_qty": good.qty,
                        "load_qty": good.qty,
                    }
                )

        res["good_line_ids"] = lines
        # STORE SNAPSHOT
        res["goods_snapshot_json"] = json.dumps(good_data_line)
        _logger.info("======LINE========%s", res)

        return res

    def _populate_goods_lines(self):
        self.ensure_one()

        lines = []
        for leg in self.leg_ids:
            booking = leg.movement_id.booking_id
            for good in booking.goods_line_ids:
                if good.qty <= 0:
                    continue

                lines.append(
                    {
                        "wizard_id": self.id,
                        "movement_leg_id": leg.id,
                        "booking_id": booking.id,
                        "docket_no": booking.docket_no,
                        "goods_type_id": good.goods_type_id.id,
                        "booking_good_line_id": good.id,
                        "weight": good.actual_weight,
                        "unit_id": good.unit_id.id,
                        "available_qty": good.qty,
                        "load_qty": good.qty,
                    }
                )
        # Remove old wizard lines first
        self.good_line_ids.unlink()
        self.env["transport.assign.manifest.line.wizard"].create(lines)
