from odoo import fields, models, api, _
from odoo.addons.queue_job.job import Job

# import xml.etree.ElementTree as etree
from lxml import etree
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    urgenza = fields.Boolean("Urgenza")
    nota = fields.Char(size=30, string="Nota")

    # firstname = fields.Char(related="partner_id.firstname", string="Nome", store=True)
    # lastname = fields.Char(related="partner_id.lastname", string="Cognome", store=True)

    firstname = fields.Char(string="Nome")
    lastname = fields.Char(string="Cognome")

    sent = fields.Boolean("Spedito", default=False)
    invio_singolo = fields.Boolean("Invio singolo", default=False)
    session_id = fields.Char("ID Sessione")

    # street = fields.Char(related="partner_id.street", string="Indirizzo", store=True)
    # street2 = fields.Char(related="partner_id.street2", string="Presso", store=True)
    # city = fields.Char(related="partner_id.city", string="Città", store=True)
    # province = fields.Char(related="partner_id.state_id.code", string="Provincia", store=True)
    # zip_code = fields.Char(related="partner_id.zip", string="Cap", store=True)
    # country = fields.Char(related="partner_id.country_id.name", string="Nazione", store=True)

    street = fields.Char(string="Indirizzo")
    street2 = fields.Char(string="Presso")
    city = fields.Char(string="Città")
    province = fields.Char(string="Provincia")
    zip_code = fields.Char(string="Cap")
    country = fields.Char(string="Nazione")

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):

        _logger.debug("Entering fields_view_get")

        res = super(SaleOrder, self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu,
        )

        if toolbar:
            actions_in_toolbar = res["toolbar"].get("action")

            if actions_in_toolbar:
                action_view = self._context["params"]["action"]

                for action in res["toolbar"]["action"][:]:

                    if action.get("xml_id"):
                        _logger.debug(
                            "========== ACTION: {}".format(action["xml_id"])
                        )

                        if (
                            action_view
                            == self.env.ref("stampa.action_sale_sent").id
                            or action_view
                            == self.env.ref("sale.action_orders").id
                            # or
                            # action_view == self.env.ref('product.product_template_action').id
                            or (
                                action_view
                                == self.env.ref("sale.action_quotations").id
                                and action["xml_id"]
                                != u"stampa.button_validate_order"
                            )
                            or (
                                action_view
                                == self.env.ref(
                                    "stampa.action_sale_sending"
                                ).id
                                and action["xml_id"]
                                != u"stampa.button_send_order"
                            )
                        ):

                            res["toolbar"]["action"].remove(action)

        return res

    def button_manda_in_spedizione(self):

        for order in self:
            order.state = "sale"
            order.confirmation_date = fields.Datetime.now()

        self.env["sale.order"].with_delay().button_manda_in_spedizione_batch(
            self
        )

    # @job
    def button_manda_in_spedizione_batch(self, other):

        if other.env.context.get("send_email"):
            other.force_quotation_send()

        for order in other:
            self.env[
                "sale.order"
            ].with_delay().custom_action_procurement_create(order)

        if other.env["ir.values"].get_default(
            "sale.config.settings", "auto_done_setting"
        ):
            other.action_done()

    # @job
    def custom_action_procurement_create(self, obj):
        obj.order_line._action_procurement_create()

    def action_server_validate_picking(self):

        for order in self:
            order.sent = True

        self.env[
            "sale.order"
        ].with_delay().action_server_validate_picking_batch(self)

    # @job
    def action_server_validate_picking_batch(self, other):

        for order in other:

            for picking in order.picking_ids:
                self.env["sale.order"].with_delay().custom_action_done(
                    order, picking
                )

    # @job
    def custom_action_done(self, order, picking):
        picking.action_done()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    message_needaction = fields.Boolean(related="order_id.message_needaction")

    name_order = fields.Char(related="order_id.name")
    date_order = fields.Datetime(related="order_id.date_order", store=True)
    partner_id = fields.Many2one(related="order_id.partner_id", store=True)

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
