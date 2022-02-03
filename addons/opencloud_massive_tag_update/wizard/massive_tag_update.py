from odoo import api, fields, models


class opencloud_massive_tag(models.TransientModel):
    _name = "opencloud.massive.tag"
    _description = "Massive Tag"

    partner_ids = fields.Many2many("res.partner", string="Partners")
    category_ids = fields.Many2many("res.partner.category", string="Tags")

    def default_get(self, fields):
        res = super(opencloud_massive_tag, self).default_get(fields)
        active_ids = self.env.context.get("active_ids")
        if (
            self.env.context.get("active_model") == "res.partner"
            and active_ids
        ):
            res["partner_ids"] = [(6, 0, active_ids)]
        return res

    def adicionar_tag(self):
        for clientes in self.partner_ids:
            lista_tags = []
            for c in clientes.category_id:
                lista_tags.append(c.id)

            for tags in self.category_ids:
                if tags.id not in lista_tags:
                    lista_tags.append(tags.id)

            clientes.write({"category_id": [[6, False, lista_tags]]})

        return True


class massive_tag_remove(models.TransientModel):
    _name = "massive.tag.remove"
    _description = "Massive Tag Remove"

    partner_ids = fields.Many2many("res.partner", string="Partners")
    category_ids = fields.Many2many("res.partner.category", string="Tags")

    def default_get(self, fields):
        res = super(massive_tag_remove, self).default_get(fields)
        active_ids = self.env.context.get("active_ids")
        if (
            self.env.context.get("active_model") == "res.partner"
            and active_ids
        ):
            res["partner_ids"] = [(6, 0, active_ids)]
        res["category_ids"] = [(6, 0, self.env["res.partner"].browse(active_ids).mapped("category_id").ids)]
        return res

    def remove_tag(self):
        for client in self.partner_ids:
            new_category_id = client.category_id - self.category_ids
            if not new_category_id:
                client.write({"category_id": [[5, False, False]]})
            else:
                client.write(
                    {"category_id": [[6, False, new_category_id.ids]]}
                )

        return True
