import base64
import hashlib
import logging
import os
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Register(models.Model):
    _name = "ew_l10n_at_pos_cert.register"
    _description = "RKSV Register"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    name = fields.Char(
        string="Name",
        copy=False,
        help="Name with which the signautre device will be registered in FinanzOnline.",
    )

    session_token = fields.Char(string="Session Token")

    is_in_use = fields.Boolean(
        string="Is In Use", compute="_compute_is_in_use", store=True
    )

    pos_config_id = fields.Many2one(
        comodel_name="pos.config", string="PoS Configuration"
    )

    signature_device_id = fields.Many2one(
        comodel_name="ew_l10n_at_pos_cert.signature_device",
        string="Signature Device",
        index=True,
    )

    aes_key_b64 = fields.Char(
        string="AES Key",
        default=lambda r: base64.b64encode(os.urandom(32)),
        copy=False,
        readonly=True,
    )

    zda_identity = fields.Char(
        string="ZDA ID", related="signature_device_id.zda_identity"
    )

    algorithm = fields.Char(string="Algorithm", related="signature_device_id.algorithm")

    certificate = fields.Text(
        string="Certificate", related="signature_device_id.certificate"
    )

    certificate_issuer = fields.Char(
        string="Certificate Issuer",
        related="signature_device_id.certificate_issuer",
    )

    certificate_serial_number = fields.Char(
        string="Certificate Serial Number",
        related="signature_device_id.certificate_serial_number",
    )

    turnover = fields.Integer(
        string="Turnover",
        default=0,
        copy=False,
        readonly=True,
        compute="_compute_last_receipt",
    )

    last_null_receipt_date = fields.Date(
        string="Date of last Null Receipt",
        copy=False,
        readonly=True,
        compute="_compute_last_null_receipt",
    )

    last_receipt_hash = fields.Char(
        string="Hash of Last Receipt",
        copy=False,
        readonly=True,
        compute="_compute_last_receipt",
    )

    receipt_counter = fields.Integer(
        string="Receipt Counter",
        default=0,
        copy=False,
        readonly=True,
        compute="_compute_last_receipt",
    )

    outage = fields.Boolean(
        string="Outage",
        copy=False,
        readonly=True,
        compute="_compute_last_receipt",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    # ----------------------------------------------------------
    # Compute
    # ----------------------------------------------------------

    @api.depends("session_token")
    def _compute_is_in_use(self):
        """
        Computes whether the register is currently in use by checking if a session token exists.

        Updates:
            is_in_use (bool): True if a session token is present; otherwise False.
        """
        for record in self:
            record.is_in_use = bool(record.session_token)

    def _compute_last_null_receipt(self):
        """
        Computes the date of the last null or start receipt for the register.

        Updates:
            last_null_receipt_date (datetime or bool): Date of the last null/start receipt
            or False if no such receipts exist.
        """
        for record in self:
            max_number_order_id = self.env["pos.order"].search(
                [
                    ("l10n_at_register_id", "=", record.id),
                    ("l10n_at_type", "in", ["NULL_RECEIPT", "START_RECEIPT"]),
                ],
                order="l10n_at_number desc",
                limit=1,
            )
            record.last_null_receipt_date = False
            if max_number_order_id:
                record.last_null_receipt_date = max_number_order_id.date_order

    def _compute_last_receipt(self):
        """
        Computes details of the last receipt issued for the register, including receipt counter,
        hash, turnover, and outage status.

        Updates:
            receipt_counter (int): The number of the last receipt.
            last_receipt_hash (str or bool): Base64-encoded hash of the last receipt's signature or False.
            turnover (float): Turnover value from the last receipt.
            outage (bool): Outage status from the last receipt.
        """
        for record in self:
            max_number_order_id = self.env["pos.order"].search(
                [("l10n_at_register_id", "=", record.id)],
                order="l10n_at_number desc",
                limit=1,
            )
            if max_number_order_id:
                record.update(
                    {
                        "receipt_counter": max_number_order_id.l10n_at_number,
                        "last_receipt_hash": base64.b64encode(
                            hashlib.sha256(
                                max_number_order_id.l10n_at_jws_signature.encode()
                            ).digest()[:8]
                        ).decode() if max_number_order_id.l10n_at_jws_signature else False ,
                        "turnover": max_number_order_id.l10n_at_turnover,
                        "outage": max_number_order_id.l10n_at_sd_not_available,
                    }
                )
            else:
                record.update(
                    {
                        "receipt_counter": 0,
                        "last_receipt_hash": False,
                        "turnover": 0,
                        "outage": False,
                    }
                )

    # ----------------------------------------------------------
    # UI Actions
    # ----------------------------------------------------------

    def action_create_dep(self):
        """
        Creates a DEP (Data Export Protocol) file for the register, containing receipt groups
        and signatures in JSON format.

        Returns:
            dict: An action dictionary to download the generated DEP file.

        Raises:
            UserError: If no receipts are found for the register.
        """
        self.ensure_one()
        order_ids = self.env["pos.order"].search(
            [("l10n_at_register_id", "=", self.id)], order="l10n_at_number asc"
        )
        if not order_ids:
            raise UserError(_("No receipts found!"))
        dep = order_ids._create_dep()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "dep-%s-%s-%s.json"
                % (
                    self.name,
                    order_ids[0].date_order.strftime("%Y-%m-%dT%H:%M:%S"),
                    order_ids[-1].date_order.strftime("%Y-%m-%dT%H:%M:%S"),
                ),
                "datas": base64.b64encode(dep.encode()),
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "target": "new",
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=1" % attachment.id,
        }

    def action_dep_check(self):
        """
        Opens the DEP Check Wizard to validate the DEP file for the register.

        Returns:
            dict: Action dictionary for the DEP Check Wizard.
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "ew_l10n_at_pos_cert.action_dep_check_wizard"
        )
        action["context"] = {"default_register_id": self.id}
        return action

    # ----------------------------------------------------------
    # POS Actions
    # ----------------------------------------------------------

    def lock_register(self):
        """
        Locks the register by generating a unique session token. Prevents other devices
        from using the register.

        Returns:
            dict: The current register record data.

        Raises:
            UserError: If the register is already in use by another device.
        """
        self.ensure_one()
        if (
            self.session_token and False
        ):  # FIXME Server side locking when session token exists (remove 'and False')
            raise UserError(_("This register is used by a different device!"))
        self.session_token = uuid.uuid4().hex
        return self.read([])[0]

    def unlock_register(self, session_token):
        """
        Unlocks the register by clearing the session token if it matches the provided token.

        Args:
            session_token (str): The session token to validate.

        Raises:
            UserError: If the session token does not match the register's current token.
        """
        self.ensure_one()
        if self.session_token != session_token:
            raise UserError(_("This register is used by a different device!"))
        self.session_token = False

    def sign(self, jws_payload):
        """
        Signs the provided JWS (JSON Web Signature) payload using the register's signature device.

        Args:
            jws_payload (str): The payload to sign.

        Returns:
            dict: A dictionary containing:
                - jws_signature (str): The complete JWS signature.
                - mrc_signature (str): A modified version of the signature for storage.
        """
        self.ensure_one()
        jws_signature = self.signature_device_id._sign(jws_payload)

        urlsafe_signature = jws_signature.split(".")[2] + "==="
        urlsafe_signature = base64.urlsafe_b64decode(urlsafe_signature)
        urlsafe_signature = base64.b64encode(urlsafe_signature).decode()

        return {
            "jws_signature": jws_signature,
            "mrc_signature": "_".join([jws_payload, urlsafe_signature]),
        }

    # ----------------------------------------------------------
    # Constrains
    # ----------------------------------------------------------

    @api.constrains("pos_config_id")
    def _check_pos_config_id(self):
        """
        Ensures that the register is correctly configured with a valid PoS configuration.

        Validates:
            - Only one register per PoS configuration is allowed unless the company allows multiple registers.
            - The PoS configuration belongs to an Austrian company.

        Raises:
            ValidationError: If the configuration violates the constraints.
        """
        for record in self.filtered("pos_config_id"):
            allow_multiple_registers = (
                record.pos_config_id.company_id.l10n_at_allow_multiple_registers
            )
            if (
                not allow_multiple_registers
                and len(record.pos_config_id.l10n_at_register_ids) > 1
            ):
                raise ValidationError(
                    _("Only one RKSV register allowed per PoS configuration!")
                )
            if not record.pos_config_id.is_company_country_austria:
                raise ValidationError(
                    _(
                        "Only PoS configurations belonging to an austrian company are allowed!"
                    )
                )

    @api.model
    def _load_pos_data_domain(self, data):
        """Constructs the domain filter for loading POS register data."""
        config_id = self.env["pos.config"].browse(data["pos.config"]["data"][0]["id"])
        return [("id", "in", config_id.l10n_at_register_ids.ids)]

    def _load_pos_data(self, data):
        """Loads POS register data based on the provided configuration."""
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data["pos.config"]["data"][0]["id"])
        registers = self.search_read(domain, fields, load=False)
        return {
            "data": registers,
            "fields": fields,
        }

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Defines the fields to be retrieved when loading POS data."""
        return [
            "name",
            "company_id",
            "aes_key_b64",
            "signature_device_id",
            "pos_config_id",
            "is_in_use",
        ]
