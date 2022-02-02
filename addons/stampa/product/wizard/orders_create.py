from odoo import api, fields, models, exceptions, _


class HeaderInvioLibroOmaggio(models.TransientModel):
    _name = "opzioni.libro.omaggio"
    _description = "Libro omaggio"
    product_id = fields.Many2one(
        "product.template", string="Libro", readonly=True
    )
    details_line = fields.One2many(
        "dettaglio.opzioni.libro.omaggio", "header_id", string="Persone"
    )
    partner_ids = fields.Many2many(
        "res.partner", string="Persone", store=False
    )
    msg_qta_superata = fields.Char(compute="_compute_qta_superata", store=True)
    invio_singolo = fields.Boolean("Invio singolo", default=False)

    @api.depends("details_line.partner_id")
    def _compute_qta_superata(self):

        giacenza = self.product_id.qty_bookable
        msg = ""
        if len(self.details_line) > giacenza:
            msg = """
                Attenzione! Quantità in magazzino non sufficiente.
                Disponibile: {}
                Richiesta: {}
            """.format(
                int(giacenza), len(self.details_line)
            )
        self.msg_qta_superata = msg

    @api.onchange("partner_ids")
    def partner_ids_change(self):

        ids = []
        for partner in self.partner_ids:
            record = self.env["dettaglio.opzioni.libro.omaggio"].create(
                {"partner_id": partner.id, "header_id": self.id}
            )
            ids.append(record.id)
        self.update({"details_line": [(6, 0, ids)]})

    def genera_step2(self):
        libro = self.product_id

        for detail in self.details_line:
            partner = detail.partner_id
            draft_order = self._get_draft_order(partner, detail)

            # TODO? E' necessario formattare la data?
            #
            tag_name = u"Lancio del {}".format(libro.data_uscita)
            tag_id = self._get_order_tag(tag_name)
            draft_order.tag_ids = tag_id

            self._set_order_product_quantity(draft_order, libro, detail)

        return True

    def _get_draft_order(self, partner_id, detail):
        if not self.invio_singolo:
            order = self.env["sale.order"].search(
                [("partner_id", "=", partner_id.id), ("state", "=", "draft")],
                limit=1,
            )
            if order:
                return order

        return self.env["sale.order"].create(
            {
                "partner_id": partner_id.id,
                "state": "draft",
                "create_ddt": True,
                "urgenza": detail.urgenza,
            }
        )

    def _get_order_tag(self, tag_name):
        CrmLeadTag = self.env["crm.tag"]

        tag_id = CrmLeadTag.search([("name", "=", tag_name)])

        if not tag_id:
            tag_id = CrmLeadTag.create({"name": tag_name})

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
            }
        )

    @api.model
    def create(self, vals):

        header = super(HeaderInvioLibroOmaggio, self).create(vals)
        header.update({"details_line": vals["details_line"]})

        return header


class DetailsInvioLibroOmaggio(models.TransientModel):
    _name = "dettaglio.opzioni.libro.omaggio"
    _description = "Opzioni libri omaggio"
    header_id = fields.Many2one("opzioni.libro.omaggio")
    partner_id = fields.Many2one("res.partner", string="Persona")
    dedica = fields.Boolean("Dedica")
    anticipo = fields.Boolean("Anticipo")
    urgenza = fields.Boolean("Urgenza")


class InvioLibriOmaggio(models.TransientModel):
    _name = "invio.libri.omaggio"
    _description = "Scelta mittenti libri omaggio"

    partner_ids = fields.Many2many("res.partner", string="Persone")
    total_selected = fields.Integer(
        "Total Selected", compute="_compute_total_selected", readonly=True
    )

    @api.model
    def default_get(self, fields):
        res = super(InvioLibriOmaggio, self).default_get(fields)
        active_ids = self.env.context.get("active_ids")
        if not active_ids:
            raise exceptions.Warning(
                u"Attenzione! " u"Nessuna libro selezionata"
            )

        if len(active_ids) > 1:
            raise exceptions.Warning(
                u"Attenzione! "
                u"E' possibile selezionale solo un libro alla volta"
            )

        return res

    def genera_step1(self):
        libro_ids = self._context.get("active_ids")
        if not self.partner_ids:
            raise exceptions.Warning(
                u"Attenzione! " u"Nessuna persona selezionata"
            )

        context = self._context.copy()
        context["qta_superata"] = True
        context["default_partner_ids"] = [p.id for p in self.partner_ids]
        context["default_product_id"] = libro_ids[0]
        view = self.env.ref("stampa.invio_libri_omaggio_wizard_view_form2")
        return {
            "name": _("Invia Libri"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "opzioni.libro.omaggio",
            "views": [(view.id, "form")],
            "type": "ir.actions.act_window",
            "target": "new",
            "context": context,
        }

    @api.depends("partner_ids")
    def _compute_total_selected(self):
        self.total_selected = len(self.partner_ids)
