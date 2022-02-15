from ast import literal_eval
from operator import itemgetter
import time
import logging

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"
    _description = "Partner"

    order = fields.One2many(
        "sale.order",
        "partner_id",
        string="Orders",
        states={"cancel": [("readonly", True)], "done": [("readonly", True)]},
        copy=True,
    )

    fax = fields.Char()
    company_type = fields.Selection(default='person')
    property_account_payable_id = fields.Many2one(required=False)
    property_account_receivable_id = fields.Many2one(required=False)

    # FIXME il field product_id nel sale.order non esiste
    # product_id = fields.Many2one(
    #    "product.product", related="order.product_id", string="Product"
    #)
    # collana_id = fields.Many2one(
    #    "stampa.collana", related="product_id.collana_id", string="Collana"
    #)

    tipo = fields.Char("Tipo", compute="_compute_type", readonly=True)

    # spostati qui da modulo ordine_import che conteneva solo questi
    codice_critico = fields.Char(string='Codice Critico', required=False, translate=True)
    codice_importazione = fields.Char(string='Codice Importazione', required=False, translate=True)
    codice_outlook = fields.Char(string='Codice Outlook', required=False, translate=True)

    @api.depends("type")
    def _compute_type(self):

        for record in self:
            record_type = str(record.type).strip().lower()

            if record_type == u"contact":
                record.tipo = u"Primario"
            elif record_type == u"delivery":
                record.tipo = u"Per spedizioni"
            elif not record_type:
                record.tipo = u""
            else:
                record.tipo = _(record_type)

    @api.model
    def create(self, vals):
        result = super(ResPartner, self).create(vals)

        # (relation, target) = ('parent_id', self.id) if not len(self.parent_id) else ('id', self.parent_id[0].id)
        # records = self.env['res.partner'].search([(relation, '=', target)])

        # for record in records:
        #     record.category_id = category_id

        return result

    def write(self, vals):

        result = super(ResPartner, self).write(vals)

        (relation, target) = (
            ("parent_id", self.id)
            if not len(self.parent_id)
            else ("id", self.parent_id[0].id)
        )
        records = self.env["res.partner"].search([(relation, "=", target)])

        for record in records:

            if "category_id" in vals:
                super(ResPartner, record).write(
                    {"category_id": vals["category_id"]}
                )
            else:
                self.update({"category_id": record["category_id"]})

        return result
