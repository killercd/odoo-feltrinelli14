# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PersonCategory(models.Model):
    _description = "Person Tags"
    _name = "stampa.person.category"
    _order = "parent_left, name"
    _parent_store = True
    _parent_order = "name"

    name = fields.Char(string="Tag Name", required=True, translate=True)
    color = fields.Integer(string="Color Index")
    parent_id = fields.Many2one(
        "stampa.person.category",
        string="Person Category",
        index=True,
        ondelete="cascade",
    )
    parent_path = fields.Char(index=True)  # aggiunto per KeyError: 'parent_path'
    child_ids = fields.One2many(
        "stampa.person.category", "parent_id", string="Child Tags"
    )
    active = fields.Boolean(
        default=True,
        help="The active field allows you to hide the category without removing it.",
    )
    parent_left = fields.Integer(string="Left parent", index=True)
    parent_right = fields.Integer(string="Right parent", index=True)

    def name_get(self):
        """Return the categories' display name, including their direct
        parent by default.

        If ``context['partner_category_display']`` is ``'short'``, the short
        version of the category name (without the direct parent) is used.
        The default is the long version.
        """
        if self._context.get("partner_category_display") == "short":
            return super(PersonCategory, self).name_get()

        res = []
        for category in self:
            names = []
            current = category
            while current:
                names.append(current.name)
                current = current.parent_id

            res.append((category.id, " / ".join(reversed(names))))

        return res

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []

        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(" / ")[-1]
            args = [("name", operator, name)] + args

        return self.search(args, limit=limit).name_get()


class Person(models.Model):
    _description = "Person"
    _name = "stampa.person"
    _order = "display_name"

    def _default_category(self):
        return self.env["stampa.person.category"].browse(
            self._context.get("category_id")
        )

    name = fields.Char(index=True)
    color = fields.Integer(string="Color Index", default=0)
    category_id = fields.Many2many(
        "stampa.person.category",
        column1="person_id",
        column2="category_id",
        string="Tags",
        default=_default_category,
    )

    active = fields.Boolean(default=True)

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_("%s (copy)") % self.name)

        return super(Person, self).copy(default)

    @api.model
    def view_header_get(self, view_id, view_type):
        res = super(Person, self).view_header_get(view_id, view_type)
        if res:
            return res

        if not self._context.get("category_id"):
            return False

        return (
            _("Person: ")
            + self.env["stampa.person.category"]
            .browse(self._context["category_id"])
            .name
        )
