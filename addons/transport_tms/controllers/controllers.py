# -*- coding: utf-8 -*-
# from odoo import http


# class TransportTms(http.Controller):
#     @http.route('/transport_tms/transport_tms', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/transport_tms/transport_tms/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('transport_tms.listing', {
#             'root': '/transport_tms/transport_tms',
#             'objects': http.request.env['transport_tms.transport_tms'].search([]),
#         })

#     @http.route('/transport_tms/transport_tms/objects/<model("transport_tms.transport_tms"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('transport_tms.object', {
#             'object': obj
#         })

