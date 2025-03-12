from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    enable_service_period = fields.Boolean(string="Has Service Period?")
    service_period_start = fields.Date(string="Service Period Start")
    service_period_end = fields.Date(string="Service Period End")
    service_date = fields.Date(string="Service Date")
