from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    is_country_austria = fields.Boolean(
        string="Company located in Austria",
        compute="_compute_is_country_austria",
    )

    l10n_at_fon_tid = fields.Char(string="Austria Fon Tid")

    l10n_at_fon_bid = fields.Char(string="Austria Fon Bid")

    l10n_at_fon_pin = fields.Char(string="Austria Fon Pin")

    l10n_at_allow_multiple_registers = fields.Boolean(
        string="Austria Allow Multiple Registers"
    )

    # ----------------------------------------------------------
    # Compute
    # ----------------------------------------------------------

    @api.depends("country_id")
    def _compute_is_country_austria(self):
        """
        Computes whether the company is based in Austria by checking the country code.

        Updates:
            is_country_austria (bool): True if the company's country code is "AT" (Austria); otherwise False.
        """
        for company in self:
            company.is_country_austria = company.country_id.code == "AT"
