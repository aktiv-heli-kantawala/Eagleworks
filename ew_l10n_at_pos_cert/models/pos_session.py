# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = "pos.session"

    @api.model
    def _load_pos_data_models(self, config_id):
        models = super()._load_pos_data_models(config_id)
        config_id = self.env["pos.config"].browse(config_id)
        if config_id.l10n_at_register_ids:
            models += ["ew_l10n_at_pos_cert.register"]
        return models

    def _loader_params_ew_l10n_at_pos_cert_register(self):
        """
        Defines the parameters for loading the `ew_l10n_at_pos_cert.register` model data
        into the POS. Restricts the data to only the registers associated with the current
        POS configuration.

        Returns:
            dict: Search parameters for loading register data.
        """
        return {
            "search_params": {
                "domain": [("id", "in", self.config_id.l10n_at_register_ids.ids)],
                "fields": ["id", "name", "is_in_use"],
                "load": False,
            }
        }

    def _get_pos_ui_ew_l10n_at_pos_cert_register(self, params):
        """
        Defines the parameters for loading the `ew_l10n_at_pos_cert.register` model data
        into the POS. Restricts the data to only the registers associated with the current
        POS configuration.

        Returns:
            dict: Search parameters for loading register data.
        """
        return self.env["ew_l10n_at_pos_cert.register"].search_read(
            **params["search_params"]
        )
