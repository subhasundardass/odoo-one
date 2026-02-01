# from odoo import models, fields, api


# class TransportDashboard(models.Model):
#     _name = "transport.dashboard"
#     _description = "TMS Dashboard"
#     _rec_name = "name"

#     name = fields.Char(default="Transport Dashboard")

#     active_deliveries = fields.Integer(compute="_compute_stats")
#     completed_today = fields.Integer(compute="_compute_stats")
#     failed_deliveries = fields.Integer(compute="_compute_stats")
#     vehicles_available = fields.Integer(compute="_compute_stats")

#     @api.model
#     def get_dashboard(self):
#         dashboard = self.search([], limit=1)
#         if not dashboard:
#             dashboard = self.create({})
#         return dashboard

#     def _compute_stats(self):
#         Delivery = self.env["transport.good.delivery"]
#         Vehicle = self.env["fleet.vehicle"]
#         today = fields.Date.today()

#         for rec in self:
#             rec.active_deliveries = Delivery.search_count(
#                 [("state", "=", "in_transit")]
#             )
#             rec.completed_today = Delivery.search_count(
#                 [("state", "=", "delivered"), ("delivery_date", "=", today)]
#             )
#             rec.failed_deliveries = Delivery.search_count([("state", "=", "failed")])
#             rec.vehicles_available = Vehicle.search_count(
#                 [("state_id.name", "=", "Available")]
#             )


from odoo import models, fields


class TransportDashboard(models.Model):
    _name = "transport.dashboard"
    _description = "TMS Dashboard"

    name = fields.Char(default="Dashboard")

    active_deliveries = fields.Integer(compute="_compute_stats", store=False)
    completed_today = fields.Integer(compute="_compute_stats", store=False)
    failed_deliveries = fields.Integer(compute="_compute_stats", store=False)
    vehicles_available = fields.Integer(compute="_compute_stats", store=False)

    def _compute_stats(self):
        Delivery = self.env["transport.good.delivery"]
        Vehicle = self.env["fleet.vehicle"]

        today = fields.Date.today()

        for rec in self:
            rec.active_deliveries = Delivery.search_count([
                ("state", "in", ["assigned", "confirmed", "out_for_delivery"])
            ])

            rec.completed_today = Delivery.search_count([
                ("state", "=", "done"),
                ("delivery_date", "=", today)
            ])

            rec.failed_deliveries = Delivery.search_count([
                ("state", "=", "failed")
            ])

            busy = Delivery.search([
                ("state", "in", ["assigned", "confirmed", "out_for_delivery"]),
                ("vehicle_id", "!=", False)
            ]).mapped("vehicle_id").ids

            rec.vehicles_available = Vehicle.search_count([
                ("id", "not in", busy)
            ])