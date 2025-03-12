import logging

from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "external", "-standard")
class RegisterTestCase(common.HttpCase):
    def setUp(self):
        super().setUp()
        self.company_id = self.env.ref("base.main_company")
        self.company_id.country_id = self.env.ref("base.at")
        self.company_id.l10n_at_allow_multiple_registers = False
        self.pos_config_id = (
            self.env["pos.config"]
            .with_context(company_id=self.company_id.id)
            .create({"name": "PC1", "company_id": self.company_id.id})
        )
        self.signature_device_id = self.env[
            "ew_l10n_at_pos_cert.signature_device"
        ].create(
            {
                "name": "SD1",
                "state": "atrust-test",
                "username": "u123456789",
                "password": "123456789",
            }
        )
        self.register_id = self.env["ew_l10n_at_pos_cert.register"].create(
            {
                "name": "RK1",
                "signature_device_id": self.signature_device_id.id,
                "pos_config_id": self.pos_config_id.id,
            }
        )

    def test_single_register_setup(self):
        result = self.pos_config_id.open_ui()
        self.assertTrue(result)
        _logger.info("RegisterTestCase.test_single_register_setup: Done")

    def test_unallowed_multi_register_setup(self):
        with self.assertRaises(ValidationError):
            self.env["ew_l10n_at_pos_cert.register"].create(
                {
                    "name": "RK2",
                    "signature_device_id": self.signature_device_id.id,
                    "pos_config_id": self.pos_config_id.id,
                }
            )
        _logger.info("RegisterTestCase.test_unallowed_multi_register_setup: Done")

    def test_multi_register_setup(self):
        self.company_id.l10n_at_allow_multiple_registers = True
        self.env["ew_l10n_at_pos_cert.register"].create(
            {
                "name": "RK2",
                "signature_device_id": self.signature_device_id.id,
                "pos_config_id": self.pos_config_id.id,
            }
        )
        result = self.pos_config_id.open_ui()
        self.assertTrue(result)
        _logger.info("RegisterTestCase.test_multi_register_setup: Done")
