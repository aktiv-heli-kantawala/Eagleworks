# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.constrains("taxes_id")
    def _check_for_austria_taxes(self):
        """
        Validates that only Austrian-specific taxes are assigned to the
        "Null Receipt" product. This ensures compliance with Austrian
        localization requirements.

        Raises:
            ValidationError: If a tax from a country other than Austria is
            assigned to the "Null Receipt" product.
        """
        if self.taxes_id.filtered(
            lambda x: x.country_id.code != "AT"
            and x.id == self.env.ref("ew_l10n_at_pos_cert.product_null_receipt").id
        ):
            raise ValidationError(
                "Taxes other than Austria specific set of taxes cannot be configured in Null Receipt"
            )
