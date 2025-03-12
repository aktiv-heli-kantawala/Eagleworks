from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # For General Ledger
    bmd_exported_general_ledger = fields.Boolean(
        string="Exported General Ledger to BMD",
        default=False,
        help="True if the data is already exported for general ledger to BMD",
        copy=False,
    )

    bmd_reexport_general_ledger = fields.Boolean(
        string="Needs to Reexport General Ledger to BMD",
        default=False,
        help="True if the data is updated and needs to be reexported for general ledger to BMD",
        copy=False,
    )

    # For Customer move
    bmd_exported_out_move = fields.Boolean(
        string="Exported Out moves Ledger to BMD",
        default=False,
        help="True if the data is already exported for Out moves to BMD",
        copy=False,
    )
    bmd_reexport_out_move = fields.Boolean(
        string="Needs to Reexport Out moves to BMD",
        default=False,
        help="True if the data is updated and needs to be reexported for In moves to BMD",
        copy=False,
    )

    # For Vendor move
    bmd_exported_in_move = fields.Boolean(
        string="Exported In moves Ledger to BMD",
        default=False,
        help="True if the data is already exported for In moves to BMD",
        copy=False,
    )
    bmd_reexport_in_move = fields.Boolean(
        string="Needs to Reexport In moves to BMD",
        default=False,
        help="True if the data is updated and needs to be reexported for In moves to BMD",
        copy=False,
    )

    # For Bank move
    bmd_exported_bank_move = fields.Boolean(
        string="Exported Bank moves Ledger to BMD",
        default=False,
        help="True if the data is already exported for Bank moves to BMD",
        copy=False,
    )

    bmd_reexport_bank_move = fields.Boolean(
        string="Needs to Reexport Bank moves to BMD",
        default=False,
        help="True if the data is updated and needs to be reexported for Bank moves to BMD",
        copy=False,
    )

    # For Cash move
    bmd_exported_cash_move = fields.Boolean(
        string="Exported Cash moves Ledger to BMD",
        default=False,
        help="True if the data is already exported for Cash moves to BMD",
        copy=False,
    )

    bmd_reexport_cash_move = fields.Boolean(
        string="Needs to Reexport Cash moves to BMD",
        default=False,
        help="True if the data is updated and needs to be reexported for Cash moves to BMD",
        copy=False,
    )

    @api.onchange(
        "account_id",
        "account_id.code",
        "account_id.account_type",
        "account_id.account_tax_id",
        "credit",
        "debit",
    )
    def onchange_bmd_fields(self):
        """
        The function `onchange_bmd_fields` sets the fields `bmd_reexport_general_ledger`
        to `True` if they are not already set on the changes of certain fields.
        """
        for res in self:
            if not res.bmd_reexport_general_ledger:
                res.bmd_reexport_general_ledger = True

    @api.onchange(
        "account_id",
        "move_name",
        "date",
        "journal_id",
        "debit",
        "credit",
        "tax_ids",
        "name",
    )
    def onchange_bmd_fields_for_move(self):
        """
        The function `onchange_bmd_fields` sets the fields `bmd_reexport_cash_move`,
        'bmd_reexport_in_move', 'bmd_reexport_out_move' and `bmd_reexport_bank_move`
        to `True` if they are not already set on the changes of certain fields.
        """
        for res in self:
            fields_to_check = [
                "bmd_reexport_out_move",
                "bmd_reexport_in_move",
                "bmd_reexport_bank_move",
                "bmd_reexport_cash_move",
            ]
            for field in fields_to_check:
                if not getattr(res, field):
                    setattr(res, field, True)
