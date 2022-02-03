# -*- coding: utf-8 -*-
# from odoo import http


# class FeltrinelliReports(http.Controller):
#     @http.route('/feltrinelli_reports/feltrinelli_reports/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/feltrinelli_reports/feltrinelli_reports/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('feltrinelli_reports.listing', {
#             'root': '/feltrinelli_reports/feltrinelli_reports',
#             'objects': http.request.env['feltrinelli_reports.feltrinelli_reports'].search([]),
#         })

#     @http.route('/feltrinelli_reports/feltrinelli_reports/objects/<model("feltrinelli_reports.feltrinelli_reports"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('feltrinelli_reports.object', {
#             'object': obj
#         })
