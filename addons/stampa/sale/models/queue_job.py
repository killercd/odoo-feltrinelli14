import logging
from datetime import datetime, timedelta

from odoo import _, api, exceptions, fields, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)



class QueueJob(models.Model):

    _inherit = "queue.job"

    TRANSITION_MAP = {
        'action_create_shipping': 'Creazione Ordini -> {}',
        'action_confirm_single': 'In lavorazione -> In spedizione',
        'action_confirm_shipping': 'In spedizione -> Spediti'
    }

    ref_order = fields.Char(string='Rif. Ordine', readonly=True)
    transition = fields.Char(string='Transizione', readonly=True)
    partner = fields.Char(string='Destinatario', readonly=True)

    def create(self, vals):
        _logger.info(vals)
        if 'model_name' in vals:
            if vals['model_name'] in ['sale.order', 'send.book'] and vals['method_name'] in self.TRANSITION_MAP:
                if  vals['model_name'] == 'sale.order':
                    so = vals['args'][0]
                    vals['ref_order'] = so.name
                    vals['partner'] = so.partner_id.name
                    vals['transition'] = self.TRANSITION_MAP.get(vals['method_name'], '')
                elif vals['model_name'] == 'send.book':
                    vals['partner'] = '[JOB DISPATCHER]'
                    vals['transition'] = self.TRANSITION_MAP.get(vals['method_name'], '').format(vals['records'][0].target)
        
        res = super(QueueJob, self).create(vals)
        



        
