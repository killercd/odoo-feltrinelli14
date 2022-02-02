# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, exceptions, _


class TagWizard(models.TransientModel):
    """
    A wizard to manage the tag affectation.
    """

    _name = "tag.wizard"
    _description = "Tag Management"

    # TypeError: Many2many fields tag.wizard.tag_ids and sale.order.tag_ids use the same table and columns
    # FIXME 
    # serve ancora questo wizard ?

    tag_ids = fields.Many2many(
        "crm.tag",
        "sale_order_tag_rel",
        "order_id",
        "tag_id",
        string="Tags",
        required=True,
    )

    # Assegnazione di un Tag a ordini multipli
    def genera_tag(self):
        order_ids = self.env.context.get("active_ids", [])
        tags = []
        for i in self.tag_ids:
            tags.append(i.id)
        for order in self.env["sale.order"].sudo().browse(order_ids):
            tags.extend(order.tag_ids)
            order.sudo().write({"tag_ids": [(6, 0, tags)]})
        return {"type": "ir.actions.act_window_close"}
