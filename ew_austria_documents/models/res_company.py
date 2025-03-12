from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    district_court = fields.Char(string="District Court")
