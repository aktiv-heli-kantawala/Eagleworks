import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SignatureDevice(models.Model):
    _name = "ew_l10n_at_pos_cert.signature_device"
    _description = "RKSV Signature Device"

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    name = fields.Char(
        string="Name",
        required=True,
        help="Name with which the signautre device will be registered in FinanzOnline.",
    )

    username = fields.Char(
        string="Username",
        required=True,
        help='Username of the selected signature device service ("Type").',
    )

    password = fields.Char(
        string="Password",
        required=True,
        help='Password of the selected signature device service ("Type").',
    )

    state = fields.Selection(
        selection=[
            ("atrust", "A-Trust"),
            ("atrust-test", "A-Trust Testserver"),
        ],
        string="Type",
        required=True,
        help="Select the signature device type.",
    )

    zda_identity = fields.Char(
        string="ZDA Identity", compute="_compute_information", store=True
    )

    algorithm = fields.Char(
        string="Algorithm", compute="_compute_information", store=True
    )

    certificate = fields.Text(
        string="Certificate", compute="_compute_information", store=True
    )

    certificate_issuer = fields.Char(
        string="Certificate Issuer", compute="_compute_information", store=True
    )

    certificate_serial_number = fields.Char(
        string="Certificate Serial Number", compute="_compute_information", store=True
    )

    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    # ----------------------------------------------------------
    # UI Actions
    # ----------------------------------------------------------

    def action_refresh_information(self):
        """
        Refreshes the information of the record by calling the _compute_information method.
        This is typically used to recompute details after any state change.
        """
        self._compute_information()

    # ----------------------------------------------------------
    # Compute
    # ----------------------------------------------------------

    @api.depends("state", "username", "password")
    def _compute_information(self):
        """
        Computes and updates information related to the signature device based on the current state, username, and password.

        The method retrieves data from an external service depending on the 'state' field value. It fetches the ZDA identity and certificate details
        using the username, password, and specific URLs based on the state. The fetched data is used to update the following fields:
            - zda_identity: The ZDA identity.
            - algorithm: The algorithm used for the certificate.
            - certificate: The certificate used for signing.
            - certificate_issuer: A JSON-encoded string of certificate issuers.
            - certificate_serial_number: The serial number of the certificate.

        Raises:
            UserError: If the 'state' is invalid or the response from the external service is not valid.
        """
        for record in self.filtered(lambda r: r.state and r.username and r.password):
            url = False
            if self.state == "atrust-test":
                url = f"https://hs-abnahme.a-trust.at/asignrkonline/v2/{self.username}/ZDA"
            elif self.state == "atrust":
                url = f"https://rksv.a-trust.at/asignrkonline/v2/{self.username}/ZDA"

            if not url:
                raise UserError(_("Invalid Signature Device Type!"))

            response = requests.get(url)
            result = response.json()

            record.zda_identity = result.get("zdaid")

            url = False
            if self.state == "atrust-test":
                url = f"https://hs-abnahme.a-trust.at/asignrkonline/v2/{self.username}/Certificate"
            elif self.state == "atrust":
                url = f"https://rksv.a-trust.at/asignrkonline/v2/{self.username}/Certificate"

            if not url:
                raise UserError(_("Invalid Signature Device Type!"))

            response = requests.get(url)
            result = response.json()
            record.update(
                {
                    "algorithm": result.get("alg"),
                    "certificate": result.get("Signaturzertifikat"),
                    "certificate_issuer": json.dumps(
                        result.get("Zertifizierungsstellen")
                    ),
                    "certificate_serial_number": result.get(
                        "ZertifikatsseriennummerHex"
                    ),
                }
            )

    # ----------------------------------------------------------
    # Helper Methods
    # ----------------------------------------------------------

    def _sign(self, jws_payload):
        """
        Signs the provided JWS payload using the signature device and the current password.

        The method constructs a URL based on the device state (either 'atrust' or 'atrust-test') and makes a POST request to the
        external service to sign the provided payload. The response's result is returned as the signature.

        Args:
            jws_payload (str): The payload to be signed.

        Returns:
            str: The signed result from the external service.

        Raises:
            UserError: If the 'state' is invalid or the signing request fails.
        """
        self.ensure_one()

        url = False
        if self.state == "atrust-test":
            url = f"https://hs-abnahme.a-trust.at/asignrkonline/v2/{self.username}/Sign/JWS"
        elif self.state == "atrust":
            url = f"https://rksv.a-trust.at/asignrkonline/v2/{self.username}/Sign/JWS"

        if not url:
            raise UserError(_("Invalid Signature Device Type!"))

        payload = {"password": self.password, "jws_payload": jws_payload}

        response = requests.post(url, data=payload)
        result = response.json().get("result")
        return result
