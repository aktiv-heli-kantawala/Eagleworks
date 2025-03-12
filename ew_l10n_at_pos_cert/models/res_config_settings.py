from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    is_company_country_austria = fields.Boolean(
        string="Company located in Austria",
        related="pos_config_id.company_id.is_country_austria",
    )

    l10n_at_register_ids = fields.One2many(
        comodel_name="ew_l10n_at_pos_cert.register",
        related="pos_config_id.l10n_at_register_ids",
        readonly=False,
        string="RKSV Registers",
    )

    l10n_at_fon_tid = fields.Char(
        related="company_id.l10n_at_fon_tid",
        string="FON Subscription ID",
        readonly=False,
    )

    l10n_at_fon_bid = fields.Char(
        related="company_id.l10n_at_fon_bid",
        string="FON User ID",
        readonly=False,
    )

    l10n_at_fon_pin = fields.Char(
        related="company_id.l10n_at_fon_pin", string="FON PIN", readonly=False
    )

    l10n_at_allow_multiple_registers = fields.Boolean(
        related="company_id.l10n_at_allow_multiple_registers",
        string="Allow Multiple Registers per PoS Config",
        readonly=False,
    )

    l10n_at_regkassen_verification_exec_path = fields.Char(
        string="Regkassen Verification Executable Path",
        config_parameter="ew_l10n_at_pos_cert.regkassen_verification_exec_path",
    )

    l10n_at_regkassen_verification_work_dir = fields.Char(
        string="Regkassen Verification Work Directory",
        config_parameter="ew_l10n_at_pos_cert.regkassen_verification_work_dir",
    )
