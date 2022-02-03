from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _order = "data_uscita desc, name"

    accantonamento = fields.Integer("Accantonamento", default=0)

    def action_view_sales(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        product_ids = self.with_context(active_test=False).product_variant_ids.ids
        action['context'] = {
            'default_product_id': str(product_ids[0])
        }
        return action


class ProductChangeQuantity(models.TransientModel):
    _inherit = "stock.change.product.qty"

    @api.constrains("new_quantity")
    def check_new_quantity(self):
        if any(wizard.new_quantity < 0 for wizard in self):
            pass  # raise UserError(_('Quantity cannot be negative.'))

    def change_product_qty(self):

        # controllo la quantità
         
        new_qty = self.product_id.qty_available + self.new_quantity
        added_qty = self.new_quantity
        self.new_quantity = new_qty

        if new_qty < 0:
            raise UserError(_("Quantity cannot be negative."))

        res = super(ProductChangeQuantity, self).change_product_qty()
        
        # aggiorno il field accantonamento
        self.product_id.accantonamento = (
            self.product_id.accantonamento + added_qty
        )