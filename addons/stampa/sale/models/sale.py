from odoo import fields, models, api, _
#from odoo.addons.queue_job.job import Job
from lxml import etree
import logging
from functools import wraps
import time
_logger = logging.getLogger(__name__)

def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'Function {func.__name__}{args} {kwargs} Took {total_time:.4f} seconds')
        return result
    return timeit_wrapper
class SaleOrder(models.Model):
    _inherit = "sale.order"

    urgenza = fields.Boolean("Urgenza")
    nota = fields.Char(size=30, string="Nota")

    firstname = fields.Char(string="Nome")
    lastname = fields.Char(string="Cognome")

    sent = fields.Boolean("Spedito", default=False)
    invio_singolo = fields.Boolean("Invio singolo", default=False)
    session_id = fields.Char("ID Sessione")

    street = fields.Char(string="Indirizzo")
    street2 = fields.Char(string="Presso")
    city = fields.Char(string="Città")
    province = fields.Char(string="Provincia")
    zip_code = fields.Char(string="Cap")
    country = fields.Char(string="Nazione")

    def action_confirm_single(self, order):
        order.action_confirm()

    def action_confirm_single_validate_picking(self, order):
        order.action_confirm()
        order.action_server_validate_picking()

    @timeit
    def button_manda_in_spedizione(self):
        for order in self:
            self.with_delay().action_confirm_single(order)

        view = self.env.ref("sh_message.sh_message_wizard")
        context = dict(self.env.context)
        context["message"] = "Schedulazione conferma ordini creata con successo. Per verificare controllare la lista nel modulo Queue Job"
        context["url"] = ""

        return {
            "name": "Schedulazione conferma ordini",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "sh.message.wizard",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "context": context,
        }

    def custom_action_procurement_create(self, obj):
        obj.order_line._action_procurement_create()

    @timeit
    def action_server_validate_picking(self):
        for order in self:
            order.sent = True
            for picking in order.picking_ids:
                picking.action_assign()
                for move in picking.move_lines:
                    move.quantity_done = move.product_uom_qty
                picking._action_done()

        view = self.env.ref("sh_message.sh_message_wizard")
        context = dict(self.env.context)
        context["message"] = "Ordini spediti con successo."
        context["url"] = ""

        return {
            "name": "Ordini spediti",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "sh.message.wizard",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "context": context,
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    message_needaction = fields.Boolean(related="order_id.message_needaction")

    name_order = fields.Char(related="order_id.name", string="Spedizione")
    date_order = fields.Datetime(related="order_id.date_order", store=True)
    partner_id = fields.Many2one(related="order_id.partner_id", store=True, string="Contatto")

    isbn = fields.Char(related="product_id.barcode")

    dedica = fields.Boolean("Dedica")
    urgenza = fields.Boolean(related="order_id.urgenza")  # store=True)
    anticipo = fields.Boolean("Anticipo")

    order_data_uscita = fields.Date(
        related="product_id.product_tmpl_id.data_uscita"
    )
    order_in_magazzino = fields.Date(
        related="product_id.in_magazzino", store=True
    )
    firstname = fields.Char(related="order_id.firstname")
    lastname = fields.Char(related="order_id.lastname")
    autori_id = fields.Many2many(related="product_id.autori_id")
    tag_ids = fields.Many2many(related="order_id.tag_ids")

    address = fields.Char(string="Indirizzo", compute="_get_address")

    @api.depends("order_id")
    def _get_address(self):

        for record in self:
            record.address = ", ".join(
                filter(
                    None,
                    [
                        record.order_id.street,
                        record.order_id.street2,
                        " ".join(
                            filter(
                                None,
                                [
                                    record.order_id.zip_code,
                                    record.order_id.city,
                                    record.order_id.province,
                                ],
                            )
                        ),
                        record.order_id.country,
                    ],
                )
            )
