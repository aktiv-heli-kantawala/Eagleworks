import logging
from datetime import datetime

import pytz

import zeep
from lxml import etree
from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class FonMessage(models.Model):
    """
    Communication with austrias financial authorities

    Documentation: https://www.bmf.gv.at/dam/jcr:19c193f4-99cd-42ff-9b23-655f2ab5734e/BMF_Registrierkassen_Webservice.pdf
    """

    _name = "ew_l10n_at_pos_cert.fon_message"
    _description = "FinanzOnline Message"

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    display_name = fields.Char(string="Display Name", compute="_compute_display_name")

    date = fields.Datetime(string="Date", default=fields.Datetime.now)

    type = fields.Selection(
        string="type",
        selection=[
            ("signature_device_registration", "Signature Device Registration"),
            ("signature_device_status", "Signature Device Status"),
            ("register_registration", "Register Registration"),
            ("register_status", "Register Status"),
        ],
    )

    signature_device_id = fields.Many2one(
        comodel_name="ew_l10n_at_pos_cert.signature_device", string="Signature Device"
    )

    register_id = fields.Many2one(
        comodel_name="ew_l10n_at_pos_cert.register", string="Register"
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        string="Company",
    )

    response = fields.Text(string="Response", readonly=True)

    # ----------------------------------------------------------
    # Compute
    # ----------------------------------------------------------

    def _compute_display_name(self):
        """
        Computes the display name for the record by combining the type label
        and the record's ID, if available.
        """
        for record in self:
            type_label = False
            for name, label in self._fields["type"].selection:
                if name == record.type:
                    type_label = label
            name_fields = []
            if type_label:
                name_fields.append(type_label)
            if record.id:
                name_fields.append(f"({record.id})")
            record.display_name = " ".join(name_fields)

    # ----------------------------------------------------------
    # UI Actions
    # ----------------------------------------------------------

    def action_send(self):
        """
        Sends a request to the FON service based on the type of operation
        (e.g., register registration or status check). Handles login, operation execution,
        and logout, while storing responses or errors.
        """
        self.ensure_one()

        session_client = zeep.Client(
            wsdl="https://finanzonline.bmf.gv.at/fonws/ws/sessionService.wsdl"
        )
        rk_client = zeep.Client(
            wsdl="https://finanzonline.bmf.gv.at/fonws/ws/regKasseService.wsdl"
        )

        if self.type in [
            "signature_device_registration",
            "signature_device_status",
        ]:
            self.company_id = self.signature_device_id.company_id
        if self.type in ["register_registration", "register_status"]:
            self.company_id = self.register_id.company_id

        session = False
        try:
            session = self._fon_login(session_client)
        except zeep.exceptions.Fault:
            raise UserError(_("Could not log in to FON Service!"))

        try:
            if hasattr(self, f"_fon_{self.type}"):
                self.response = str(
                    getattr(self, f"_fon_{self.type}")(session, rk_client)
                )
            else:
                raise NotImplementedError(_("This function is not implemented yet!"))
        except zeep.exceptions.Fault as e:
            self.response = etree.tostring(
                e.detail,
                pretty_print=True,
                xml_declaration=True,
                encoding="utf-8",
            ).decode("utf-8")
            _logger.exception(e)

        try:
            self._fon_logout(session, session_client)
        except zeep.exceptions.Fault as e:
            _logger.exception(e)

    # ----------------------------------------------------------
    # Fon Methods
    # ----------------------------------------------------------

    def _fon_register_registration(self, session, rk_client):
        """
        Executes the register registration request to the FON service using the given session
        and rk_client, returning the service response.
        """
        return rk_client.service.rkdb(
            rkdb={
                "paket_nr": 1,
                "ts_erstellung": datetime.strftime(
                    datetime.now(tz=pytz.timezone("Europe/Vienna")),
                    "%Y-%m-%dT%H:%M:%S",
                ),
                "registrierung_kasse": {
                    "satznr": 1,
                    "kassenidentifikationsnummer": self.register_id.name,
                    "benutzerschluessel": self.register_id.aes_key_b64,
                },
            },
            tid=self.company_id.l10n_at_fon_tid,
            benid=self.company_id.l10n_at_fon_bid,
            id=session,
            erzwinge_asynchron=0,
            art_uebermittlung="P",
        )

    def _fon_register_status(self, session, rk_client):
        """
        Executes the register status request to the FON service using the given session
        and rk_client, returning the service response.
        """
        return rk_client.service.rkdb(
            status_kasse={
                "paket_nr": 1,
                "ts_erstellung": datetime.strftime(
                    datetime.now(tz=pytz.timezone("Europe/Vienna")),
                    "%Y-%m-%dT%H:%M:%S",
                ),
                "satznr": 1,
                "kassenidentifikationsnummer": self.register_id.name,
            },
            tid=self.company_id.l10n_at_fon_tid,
            benid=self.company_id.l10n_at_fon_bid,
            id=session,
            erzwinge_asynchron=0,
            art_uebermittlung="P",
        )

    def _fon_receipt_verification(self, session, rk_client):
        """
        Placeholder method for receipt verification functionality.
        Raises a NotImplementedError.
        """
        raise NotImplementedError(_("This function is not implemented yet!"))

    def _fon_signature_device_registration(self, session, rk_client):
        """
        Executes the signature device registration request to the FON service using the
        given session and rk_client, returning the service response.
        """
        return rk_client.service.rkdb(
            rkdb={
                "paket_nr": 1,
                "ts_erstellung": datetime.strftime(
                    datetime.now(tz=pytz.timezone("Europe/Vienna")),
                    "%Y-%m-%dT%H:%M:%S",
                ),
                "registrierung_se": {
                    "satznr": 1,
                    "art_se": "HSM_DIENSTLEISTER",
                    "vda_id": self.signature_device_id.zda_identity,
                    "zertifikatsseriennummer": self.signature_device_id.certificate_serial_number,
                },
            },
            tid=self.company_id.l10n_at_fon_tid,
            benid=self.company_id.l10n_at_fon_bid,
            id=session,
            erzwinge_asynchron=0,
            art_uebermittlung="P",
        )

    def _fon_signature_device_status(self, session, rk_client):
        """
        Executes the signature device status request to the FON service using the
        given session and rk_client, returning the service response.
        """
        return rk_client.service.rkdb(
            status_see={
                "paket_nr": 1,
                "ts_erstellung": datetime.strftime(
                    datetime.now(tz=pytz.timezone("Europe/Vienna")),
                    "%Y-%m-%dT%H:%M:%S",
                ),
                "satznr": 1,
                "zertifikatsseriennummer": self.signature_device_id.certificate_serial_number,
            },
            tid=self.company_id.l10n_at_fon_tid,
            benid=self.company_id.l10n_at_fon_bid,
            id=session,
            erzwinge_asynchron=0,
            art_uebermittlung="P",
        )

    def _fon_login(self, session_client):
        """
        Executes the signature device status request to the FON service using the
        given session and rk_client, returning the service response.
        """
        result = session_client.service.login(
            tid=self.company_id.l10n_at_fon_tid,
            benid=self.company_id.l10n_at_fon_bid,
            pin=self.company_id.l10n_at_fon_pin,
            herstellerid="ATU72178118",
        )
        if result.rc == 0:
            session = result.id
        else:
            raise UserError(_("Could not log in to FON Service!"))
        return session

    def _fon_logout(self, session, session_client):
        """
        Logs out from the FON service using the provided session ID and session client.
        """
        session_client.service.logout(
            tid=self.company_id.l10n_at_fon_tid,
            benid=self.company_id.l10n_at_fon_bid,
            id=session,
        )
