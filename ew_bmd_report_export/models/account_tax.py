from odoo import models, fields


class AccountTax(models.Model):
    _inherit = "account.tax"

    bmd_steuercode = fields.Char(string="BMD Steuercode")
