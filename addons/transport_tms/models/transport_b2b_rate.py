from odoo import models, fields, api
from datetime import date


class TransportB2BRate(models.Model):
    _name = "transport.b2b.rate"
    _description = "B2B Transport Rate"
    _order = "valid_from desc"

    name = fields.Char(
        string="Rate Reference",
        default="New",
        copy=False,
    )

    transporter_id = fields.Many2one(
        "res.partner",
        string="Transporter",
        domain=[("partner_type", "=", "customer_b2b")],
        help="Leave empty for Base Rate",
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Rate UoM",
        required=True,
        help="Rate applicable per selected unit",
    )

    rate = fields.Float(string="Rate Amount", required=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )

    valid_from = fields.Date(string="Valid From", required=True)
    valid_upto = fields.Date(string="Valid Upto", required=True)
    active = fields.Boolean(default=True)

    remarks = fields.Text(string="Remarks")

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("transport.b2b.rate") or "New"
            )
        return super().create(vals)

    @api.model
    def get_b2b_rate(self, transporter_id, uom_id):
        """
        Returns rate record or False
        """
        return self.search(
            [
                ("transporter_id", "=", transporter_id),
                ("uom_id", "=", uom_id),
                ("active", "=", True),
            ],
            limit=1,
        )

    @api.model
    def get_applicable_b2b_rate(
        self,
        *,
        party_id=None,
        uom_id,
        rate_date=None,
    ):
        """
        Priority:
        1. Transporter-specific B2B rate (date valid)
        2. Base B2B rate (no transporter)
        """

        rate_date = rate_date or date.today()

        domain_date = [
            ("valid_from", "<=", rate_date),
            "|",
            ("valid_upto", "=", False),
            ("valid_upto", ">=", rate_date),
            ("active", "=", True),
            ("uom_id", "=", uom_id),
        ]

        # 1️⃣ Transporter-specific rate
        if party_id:
            customer_rate = self.search(
                domain_date + [("transporter_id", "=", party_id)],
                order="valid_from desc",
                limit=1,
            )
            if customer_rate:
                return {
                    "rate": customer_rate.rate,
                    "source": "customer",
                    "rate_id": customer_rate.id,
                }

        # 2️⃣ Base rate (transporter_id = False)
        base_rate = self.search(
            domain_date + [("transporter_id", "=", False)],
            order="valid_from desc",
            limit=1,
        )

        if base_rate:
            return {
                "rate": base_rate.rate,
                "source": "base",
                "rate_id": base_rate.id,
            }

        # 3️⃣ No rate found
        return {
            "rate": 0.0,
            "source": "none",
            "rate_id": False,
        }
