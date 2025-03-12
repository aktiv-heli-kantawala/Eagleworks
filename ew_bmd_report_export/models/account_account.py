from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    code = fields.Char(store=True)
