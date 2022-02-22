from odoo import api, fields, models, exceptions, _
from odoo.addons.queue_job.job import Job

from functools import wraps
import uuid
import logging
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

class SendBook(models.Model):
    _name = "send.book"
    _description = "Invio Titoli"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, user_id asc"

    target = fields.Selection(
        string="Destinazione: ",
        selection=[("lavorazione", "In Lavorazione"), ("spediti", "Spediti")],
        default="lavorazione",
        track_visibility="onchange",
        required=True,
        help="Campo obbligatorio.",
    )


    @timeit
    def create_delivery_order(self):
        # self.session_id = u"{}".format(uuid.uuid1())
        orders = []
        for detail in self.details_line:
            libro = detail.titolo_id
            partner = detail.partner_id
            draft_order = self._get_draft_order(partner, detail)

            if draft_order not in orders:
                orders.append(draft_order)

            tag_name = u"Lancio del {}".format(
                libro.data_uscita if libro.data_uscita else ""
            )
            tag_id = self._get_order_tag(tag_name)

            if not self.invio_singolo:
                draft_order.tag_ids = tag_id
            else:
                tag_name = ""
                tag_id = self._get_order_tag(tag_name)
                draft_order.tag_ids = tag_id

            # draft_order.tag_ids = tag_id

            titolo = self.env["product.product"].search(
                [("product_tmpl_id", "=", detail.titolo_id.id)]
            )

            self._set_order_product_quantity(draft_order, titolo, detail)

        for order in orders:
            _logger.info(
                u"[CREAZIONE TITOLI] ---> {} - SO: {} - Destinatario: {} {} - Operatore: {}".format(
                    self.target,
                    order.id,
                    order.firstname,
                    order.lastname,
                    self.user_id.name,
                )
            )

        message = "Ordini in lavorazione creati con successo"

        if self.target == "spediti":

            for order in orders:
                self.env['sale.order'].with_delay().action_confirm_single_validate_picking(order)

            message = "Schedulazione creazione ordini spediti creata con successo. Per verificare controllare la lista nel modulo Queue Job"

        view = self.env.ref("sh_message.sh_message_wizard")
        context = dict(self.env.context)
        context["message"] = message
        context["url"] = ""

        return {
            "name": "Ordini di spedizioni",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "sh.message.wizard",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "context": context,
        }

    def _get_draft_order(self, partner_id, detail):

        libro = detail.titolo_id

        if not self.invio_singolo:
            tag_name = u"Lancio del {}".format(
                libro.data_uscita if libro.data_uscita else ""
            )
            crm_lead_tag = self.env["crm.tag"]
            tag_id = crm_lead_tag.search([("name", "=", tag_name)])
            domain = [
                ("partner_id", "=", partner_id.id),
                ("state", "=", "draft"),
                ("invio_singolo", "=", self.invio_singolo),
                ("tag_ids", "=", tag_id.id),
            ]
        else:
            domain = [
                ("partner_id", "=", partner_id.id),
                ("state", "=", "draft"),
                ("invio_singolo", "=", self.invio_singolo),
                # ("session_id", "=", self.session_id),
            ]

        order = self.env["sale.order"].search(domain, limit=1)
        if (self.target != 'spediti') and order:
            return order
        else:
            return self.env["sale.order"].create(
                {
                    "partner_id": partner_id.id,
                    "state": "draft",
                    # "create_ddt": True, # non essendoci il modulo l10n_it_ddt/models/sale.py devo commentare questo campo
                    "urgenza": detail.urgenza,
                    "invio_singolo": self.invio_singolo,
                    "firstname": partner_id.firstname,
                    "lastname": partner_id.lastname,
                    "street": partner_id.street,
                    "street2": partner_id.street2,
                    "city": partner_id.city,
                    "province": partner_id.state_id.code,
                    "zip_code": partner_id.zip,
                    "country": partner_id.country_id.name,
                    # "session_id": self.session_id,  #commentato per AttributeError: 'send.book' object has no attribute 'session_id'
                    # non ho trovato nessuna definizione del campo session_id nel model send.book FIXME
                }
            )

    def _get_order_tag(self, tag_name):

        crm_lead_tag = self.env["crm.tag"]
        tag_id = crm_lead_tag.search([("name", "=", tag_name)])

        if not tag_id:
            tag_id = crm_lead_tag.create({"name": tag_name})

        return tag_id

    def _set_order_product_quantity(self, order, product, details):

        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": product.id,
                "name": product.name,
                "price_unit": 0.0,
                "product_uom": 1,
                "product_uom_qty": 1,
                "anticipo": details.anticipo,
                "dedica": details.dedica,
                "urgenza": details.urgenza,
            }
        )

    def create_send_book_line(self):
        msg_already_sent = ["Controllo duplicati"]
        anomalia_giacenze = False
        anomalia_duplicati = False
        msg_duplicazione = []
        ids = []
        for partner in self.partner_ids:
            for titolo in self.titoli_ids:
                order_lines = self.prodotti_duplicati(titolo, partner)
                if len(order_lines) > 0:
                    anomalia_duplicati = True
                    for order_i in order_lines:
                        msg_duplicazione.append(
                            u"Il prodotto '{}' è già stato inviato a {} {} nell'ordine {}".format(
                                order_i.display_name,
                                order_i.firstname,
                                order_i.lastname,
                                order_i.name_order,
                            )
                        )

                (dedica, anticipo, urgenza) = [False] * 3
                for detail in self.details_line:

                    if detail.titolo_id.id == titolo.id:
                        (dedica, anticipo, urgenza) = (
                            detail.dedica,
                            detail.anticipo,
                            detail.urgenza,
                        )
                        break

                vals = {
                    "partner_id": partner.id,
                    "titolo_id": titolo.id,
                    "header_id": self.id,
                    "dedica": dedica,
                    "anticipo": anticipo,
                    "urgenza": urgenza,
                }
                record = self.env["send.book.line"].create(vals)
                ids.append(record.id)
        self.details_line = [(6, 0, ids)]

        # controllo giacenza e invio duplicato
        alert_msg = []
        alert_msg.extend(msg_already_sent)

        if not anomalia_duplicati:
            alert_msg.extend([" - nessuna anomalia"])
        else:
            alert_msg.extend(msg_duplicazione)

        alert_msg.extend(["", "Controllo giacenza"])

        for book in self.titoli_ids:
            books = self.details_line.filtered(
                lambda line: line.titolo_id == book
            )
            if len(books) > book.qty_bookable:
                anomalia_giacenze = True
                msg = u" - Titolo: {}, Quantità richieste: {}, Quantità disponibili: {}".format(
                    book.name, len(books), book.qty_bookable
                )
                alert_msg.append(msg)
        if not anomalia_giacenze:
            alert_msg.append(" - nessuna anomalia")

        if alert_msg:
            view = self.env.ref("sh_message.sh_message_wizard")
            context = dict(self.env.context)
            context["message"] = "\n".join(alert_msg)
            context["url"] = ""

            return {
                "name": "Controllo duplicati e controllo giacenza",
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "sh.message.wizard",
                "views": [(view.id, "form")],
                "view_id": view.id,
                "target": "new",
                "context": context,
            }

    def prodotti_duplicati(self, titolo, partner):

        id_product = self.env["product.product"].search(
            [("product_tmpl_id", "=", titolo.id)]
        )
        order_lines = self.env["sale.order.line"].search(
            [
                ("partner_id", "in", self.get_associate_partner_list(partner)),
                ("product_id", "=", id_product.id),
                ("state", "in", ["draft", "sale", "sent"]),
            ]
        )
        return order_lines

    def get_associate_partner_list(self, partner):

        partner_id_list = []
        partner_id_list.append(partner.id)

        if partner.codice_critico and partner.codice_critico is not False:
            id_partner_associati = self.env["res.partner"].search(
                [("codice_critico", "=", partner.codice_critico)]
            )
            for resid in id_partner_associati:
                partner_id_list.append(resid.id)
        return partner_id_list

    @api.depends("user_id", "create_date")
    def _compute_send_book_name(self):
        self.name = "{} - {}".format(self.user_id.name, self.create_date)

    partner_ids = fields.Many2many("res.partner", string="Destinatari")
    titoli_ids = fields.Many2many("product.template", string="Titoli")
    details_line = fields.One2many(
        "send.book.line", "header_id", string="Titoli da inviare"
    )
    # msg_qta_superata = fields.Char(readonly=True)
    invio_singolo = fields.Boolean("Invio singolo", default=False)
    stato = fields.Boolean("Stato", default=False)

    user_id = fields.Many2one(
        "res.users",
        string="Operatore",
        default=lambda self: self.env.user,
        readonly=True,
    )

    create_date = fields.Datetime("Create Date", readonly=True)
    write_date = fields.Datetime("Update Date", readonly=True)
    name = fields.Char(
        "Nome", compute="_compute_send_book_name", readonly=True
    )


class SendBookLine(models.Model):
    _name = "send.book.line"
    _description = "Dettaglio Invio Libri"

    header_id = fields.Many2one("send.book")
    partner_id = fields.Many2one("res.partner", string="Destinatario")
    titolo_id = fields.Many2one("product.template", string="Titolo")
    dedica = fields.Boolean("Dedica", store=True)
    anticipo = fields.Boolean("Anticipo")
    urgenza = fields.Boolean("Urgenza")
