import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = "pos.order"

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    l10n_at_register_id = fields.Many2one(
        comodel_name="ew_l10n_at_pos_cert.register",
        string="RKSV Register",
        readonly=False,
    )

    l10n_at_number = fields.Integer(string="RKSV Number", readonly=True)

    l10n_at_turnover = fields.Integer(string="RKSV Turnover", readonly=True)

    l10n_at_type = fields.Selection(
        selection=[
            ("START_RECEIPT", "Start Receipt"),
            ("STANDARD_RECEIPT", "Standard Receipt"),
            ("REVERSAL_RECEIPT", "Reversal Receipt"),
            ("TRAINING_RECEIPT", "Training Receipt"),
            ("NULL_RECEIPT", "Null Receipt"),
        ],
        string="RKSV Type",
        readonly=True,
    )

    l10n_at_jws_signature = fields.Char(string="RKSV JWS Signature", readonly=True)

    l10n_at_mrc_signature = fields.Char(string="RKSV MRC Signature", readonly=True)

    l10n_at_certificate = fields.Text(string="RKSV Certificate", readonly=True)

    l10n_at_certificate_issuer = fields.Text(
        string="RKSV Certificate Issuer", readonly=True
    )

    l10n_at_sd_not_available = fields.Boolean(
        string="RKSV Signature Device Not Available", readonly=True
    )

    # ----------------------------------------------------------
    # Helper Methods
    # ----------------------------------------------------------

    def _create_dep(self):
        """
        Creates the Datenerfassungsprotokoll (DEP) data structure in JSON format.
        Groups the records based on their signature certificates and appends
        compact receipt data to the appropriate group. Returns the formatted
        JSON as a string.
        """
        data = {"Belege-Gruppe": []}
        group = {}

        for record in self:
            if not group or group["Signaturzertifikat"] != record.l10n_at_certificate:
                if group:
                    data["Belege-Gruppe"].append(group)
                group = {
                    "Signaturzertifikat": record.l10n_at_certificate,
                    "Zertifizierungsstellen": json.loads(
                        record.l10n_at_certificate_issuer
                    ),
                    "Belege-kompakt": [],
                }

            group["Belege-kompakt"].append(record.l10n_at_jws_signature)

        data["Belege-Gruppe"].append(group)

        return json.dumps(data, indent=4, separators=(",", ": "))

    @api.model
    def _order_fields(self, ui_order):
        """
        Extends the method to include specific Austrian localization fields in the
        order data if the company's country is set to Austria. These fields are related
        to RKSV compliance.

        Args:
            ui_order (dict): The order data received from the UI.

        Returns:
            dict: Updated order fields.
        """
        fields = super()._order_fields(ui_order)
        if self.env.company.is_country_austria and "l10n_at_register_id" in ui_order:
            fields.update(
                {
                    field_name: ui_order[field_name]
                    for field_name in [
                        "l10n_at_register_id",
                        "l10n_at_number",
                        "l10n_at_turnover",
                        "l10n_at_type",
                        "l10n_at_jws_signature",
                        "l10n_at_mrc_signature",
                        "l10n_at_certificate",
                        "l10n_at_certificate_issuer",
                        "l10n_at_sd_not_available",
                    ]
                }
            )
        return fields


    def _export_for_ui(self, order):
        """
        Prepares the order data for export to the UI. Adds Austrian-specific fields
        if the company's country is set to Austria.
        """
        json = super()._export_for_ui(order)
        if self.env.company.is_country_austria:
            json.update(
                {
                    "l10n_at_register_id": order.l10n_at_register_id,
                    "l10n_at_number": order.l10n_at_number,
                    "l10n_at_turnover": order.l10n_at_turnover,
                    "l10n_at_type": order.l10n_at_type,
                    "l10n_at_jws_signature": order.l10n_at_jws_signature,
                    "l10n_at_mrc_signature": order.l10n_at_mrc_signature,
                    "l10n_at_certificate": order.l10n_at_certificate,
                    "l10n_at_certificate_issuer": order.l10n_at_certificate_issuer,
                    "l10n_at_sd_not_available": order.l10n_at_sd_not_available,
                }
            )
        return json

    # ----------------------------------------------------------
    # UI Actions
    # ----------------------------------------------------------

    def refund(self):
        """
        Restricts refunds for orders associated with RKSV registers to be
        processed only through the POS Cashier interface. Raises a UserError if
        an attempt is made to refund directly. Otherwise, invokes the base refund method.
        """
        if self.filtered(lambda x: x.config_id.l10n_at_register_ids):
            raise UserError(
                _("You can only refund a customer from the POS Cashier interface")
            )
        return super().refund()
