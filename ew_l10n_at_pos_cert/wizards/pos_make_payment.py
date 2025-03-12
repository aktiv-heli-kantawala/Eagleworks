from odoo import _, models
from odoo.exceptions import UserError


class PosMakePayment(models.TransientModel):
    _inherit = "pos.make.payment"

    def check(self):
        if not self.config_id or self.config_id.l10n_at_mrc_signature_device_id:
            raise UserError(
                _("You can only pay an order from the POS Cashier interface")
            )
        return super().check()
