from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    code = fields.Char(
        string="Code",
        size=64,
        tracking=True,
        compute="_compute_code",
        search="_search_code",
        inverse="_inverse_code",
        store=True,
        precompute=True,
    )
