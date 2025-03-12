from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    is_company_country_austria = fields.Boolean(
        string="Company located in Austria",
        related="company_id.is_country_austria",
    )

    l10n_at_register_ids = fields.One2many(
        comodel_name="ew_l10n_at_pos_cert.register",
        inverse_name="pos_config_id",
        string="RKSV Registers",
    )

    l10n_at_null_receipt_product_id = fields.Many2one(
        string="Null Receipt Product",
        comodel_name="product.product",
        compute="_compute_l10n_at_null_receipt_product_id",
    )

    # ----------------------------------------------------------
    # UI Actions
    # ----------------------------------------------------------

    def _compute_l10n_at_null_receipt_product_id(self):
        """
        Computes and sets the 'l10n_at_null_receipt_product_id' field by referencing
        a specific product (null receipt product) defined in the module.
        """
        self.write(
            {
                "l10n_at_null_receipt_product_id": self.env.ref(
                    "ew_l10n_at_pos_cert.product_null_receipt"
                ).id
            }
        )

    # ----------------------------------------------------------
    # UI Actions
    # ----------------------------------------------------------

    def action_create_dep(self):
        """
        Triggers the creation of a DEP (Datenerfassungsprotokoll) file for the associated
        RKSV register(s). Ensures only one RKSV register is assigned; otherwise, raises a UserError.
        """
        self.ensure_one()
        if len(self.l10n_at_register_ids) == 0:
            raise UserError(
                _(
                    "No RKSV register assigned to this pos configuration. Please assign "
                    "RKSV register from 'Configuration > Settings > RKSV'"
                )
            )
        elif len(self.l10n_at_register_ids) > 1:
            raise UserError(
                _(
                    "You have more than one RKSV register assigned to this pos configuration. Please create "
                    "the DEP files in the specific RKSV registers."
                )
            )
        return self.l10n_at_register_ids.action_create_dep()

    def action_dep_check(self):
        """
        Triggers a DEP check for the associated RKSV register(s). Ensures only one RKSV register
        is assigned; otherwise, raises a UserError.
        """
        self.ensure_one()
        if len(self.l10n_at_register_ids) == 0:
            raise UserError(
                _(
                    "No RKSV register assigned to this pos configuration. Please assign "
                    "RKSV register from 'Configuration > Settings > RKSV'"
                )
            )
        if len(self.l10n_at_register_ids) > 1:
            raise UserError(
                _(
                    "You have more than one RKSV register assigned to this pos configuration. Please run "
                    "the DEP Check in the specific RKSV registers."
                )
            )
        return self.l10n_at_register_ids.action_dep_check()

    def open_ui(self):
        """
        Opens the PoS interface. Ensures that the company has a country set;
        otherwise, raises a UserError.
        """
        if not self.company_id.country_id:
            raise UserError(_("You have to set a country in your company setting."))
        return super().open_ui()

    # ----------------------------------------------------------
    # Constrains
    # ----------------------------------------------------------

    @api.constrains("l10n_at_register_ids")
    def _check_l10n_at_register_ids(self):
        """
        Ensures that the number of RKSV registers assigned to a PoS configuration adheres
        to company policy. Raises a ValidationError if multiple registers are assigned
        without permission.
        """
        if self.filtered(
            lambda x: not x.company_id.l10n_at_allow_multiple_registers
            and len(x.l10n_at_register_ids) > 1
        ):
            raise ValidationError(
                _("Only one RKSV register allowed per PoS configuration!")
            )
