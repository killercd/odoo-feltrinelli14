# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)

class ProductChangeQuantity(models.TransientModel):
    _inherit = "stock.change.product.qty"

    @api.constrains("new_quantity")
    def check_new_quantity(self):
        if any(wizard.new_quantity < 0 for wizard in self):
            pass  # raise UserError(_('Quantity cannot be negative.'))

    def change_product_qty(self):

        # controllo la quantità
        '''
        new_qty = self.product_id.qty_available + self.new_quantity
        added_qty = self.new_quantity
        self.new_quantity = new_qty

        if new_qty < 0:
            raise UserError(_("Quantity cannot be negative."))
        '''
        res = super(ProductChangeQuantity, self).change_product_qty()
        '''
        # aggiorno il field accantonamento
        self.product_id.accantonamento = (
            self.product_id.accantonamento + added_qty
        )
        '''

class Collana(models.Model):
    _description = "Collana"
    _name = "stampa.collana"

    name = fields.Char(string="Collana", required=True)


class ProductProduct(models.Model):
    _inherit = ["product.template"]
    _order = "data_uscita desc, name"

    numero_pagine = fields.Integer("Numero pagine", default=0)

    type = fields.Selection(default="product")

    book_type = fields.Char(string="Tipo Libro", size=255)
    data_uscita = fields.Date(string="In libreria")
    in_magazzino = fields.Date(string="In magazzino")
    data_cedola = fields.Date(string="Cedola")
    nome_cedola = fields.Char(string="Nome cedola", size=255)

    autori_id = fields.Many2many(
        "stampa.person", "product_person_autori_rel", string="Autore/i"
    )
    curatori_id = fields.Many2many(
        "stampa.person", "product_person_curatori_rel", string="Curatore/i"
    )
    prefatori_id = fields.Many2many(
        "stampa.person", "product_person_prefatori_rel", string="Prefatore/i"
    )
    traduttori_id = fields.Many2many(
        "stampa.person", "product_person_traduttori_rel", string="Traduttore/i"
    )
    illustratori_id = fields.Many2many(
        "stampa.person",
        "product_person_illustratori_rel",
        string="Illustratore/i",
    )

    redazione = fields.Char(String="Redazione")
    marchio_editoriale = fields.Char(String="Marchio Editoriale")

    qty_bookable = fields.Float(
        "Quantità Prenotabile",
        compute="_compute_quantities_bookable",
        digits=(0, 0)
    )
    collana_id = fields.Many2one("stampa.collana", string="Collana")

    accantonamento = fields.Integer("Accantonamento", default=0)

    selectable_fields = [
        "autori_id",
        "name",
        "collana_id",
        "data_uscita",
        "in_magazzino",
        "book_type",
        "curatori_id",
        "prefatori_id",
        "traduttori_id",
        "illustratori_id",
    ]

    def action_view_sales(self):
        # import pdb;pdb.set_trace()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.act_res_partner_2_sale_order")
        product_ids = self.with_context(active_test=False).product_variant_ids.ids
        action['context'] = {
            'search_default_product_id': product_ids[0]
        }
        _logger.info(action)
        return action

    # FIXME commentato codice per nascondere le voci superflue 
    # dalla tendina dei filtri 
    # raise exception.with_traceback(None) from new_cause
    # KeyError: 'pricelist_id'

    # @api.model
    # def fields_get(self, fields=None, attributes=None):
    #     res = super(ProductProduct, self).fields_get(
    #         fields, attributes=attributes
    #     )
    #     not_selectable_fields = set(self._fields.keys()) - set(
    #         self.selectable_fields
    #     )
    #     for field in not_selectable_fields:
    #         res[field]["selectable"] = False
    #     return res

    def _compute_quantities_bookable(self):
        SaleOrderLine = self.env["sale.order.line"]
        for prodotto in self:
            domain_sale_order_line = [
                ("product_id", "=", prodotto.product_variant_id.id),
                ("state", "in", ("draft", "sent")),
            ]
            qta_iniziale = prodotto.qty_available
            order = SaleOrderLine.read_group(
                domain_sale_order_line,
                ["product_id", "product_uom_qty"],
                ["product_id"],
            )
            if order:
                qta_prenotata = order[0]["product_uom_qty"]
                prodotto.qty_bookable = qta_iniziale - qta_prenotata

            else:
                prodotto.qty_bookable = qta_iniziale

    def name_get(self):
        return [
            (
                template.id,
                "{} - {}".format(
                    template.name, template.book_type or ""
                ),
            )
            for template in self
        ]


class ProductP(models.Model):
    _description = "Product"
    _inherit = ["product.product"]

    def _compute_sales_count(self):
        for product in self:
            product = self.env['product.product'].browse(product.id)

            so_line = self.env['sale.order.line'].search([('product_id.id', '=', product.id)])
            product.sales_count = len(so_line)

        

    def name_get(self):

        return [
            (
                product.id,
                "{} - {}".format(
                    product.name, product.book_type or ""
                ),
            )
            for product in self
        ]
