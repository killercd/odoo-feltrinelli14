import logging
from datetime import datetime, timedelta

from odoo import _, api, exceptions, fields, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)



class QueueJob(models.Model):

    _inherit = "queue.job"

    ADMITTED_METHOD = ['action_confirm_single_validate_picking', 'action_confirm_single']

    TRANSITION_MAP = {
        'action_confirm_single_validate_picking': 'Creazione Titoli -> Spedito',
        'action_confirm_single': 'In lavorazione -> In spedizione'
    }

    ref_order = fields.Char(string='Rif. Ordine', readonly=True)
    transition = fields.Char(string='Transizione', readonly=True)
    partner = fields.Char(string='Destinatario', readonly=True)

    def create(self, vals_list):
        if 'model_name' in vals_list:
            if vals_list['model_name'] == 'sale.order' and vals_list['method_name'] in self.ADMITTED_METHOD:
                so = vals_list['args'][0]
                vals_list['ref_order'] = so.name
                vals_list['transition'] = self.TRANSITION_MAP.get(vals_list['method_name'], '')
                vals_list['partner'] = so.partner_id.name
        
        res = super(QueueJob, self).create(vals_list)
        



        
