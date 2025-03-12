from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    bmd_exported_customer = fields.Boolean(
        string="Customer Exported to BMD",
        default=False,
        help="True if the customer data is already exported for BMD",
        copy=False,
    )
    bmd_reexport_customer = fields.Boolean(
        string="Customer Needs to reexport to BMD",
        default=False,
        help="True if the customer data is updated and needs to be reexported for BMD",
        copy=False,
    )

    bmd_exported_supplier = fields.Boolean(
        string="Supplier Exported to BMD",
        default=False,
        help="True if the supplier data is already exported for BMD",
        copy=False,
    )
    bmd_reexport_supplier = fields.Boolean(
        string="Supplier Needs to reexport to BMD",
        default=False,
        help="True if the supplier data is updated and needs to be reexported for BMD",
        copy=False,
    )
    debtor_number = fields.Integer(string="Debtor Number", copy=False)  # Customer
    creditor_number = fields.Integer(string="Creditor Number", copy=False)  # Supplier
    contact_type = fields.Selection(
        selection=[
            ("customer", "Debtor"),
            ("vendor", "Creditor"),
            ("none", "None"),
        ],
        default="none",
        compute="_compute_contact_type",
        store=True,
        string="Contact Type",
    )

    @api.depends("customer_rank", "supplier_rank")
    def _compute_contact_type(self):
        for rec in self:
            if rec.customer_rank > 0:
                rec.contact_type = "customer"
            elif rec.supplier_rank > 0:
                rec.contact_type = "vendor"
            else:
                rec.contact_type = "none"

    @api.onchange(
        "name",
        "title",
        "function",
        "street",
        "street2",
        "zip",
        "city",
        "country_id",
        "vat",
        "email",
        "website",
        "phone",
        "bank_ids",
        "bank_ids.acc_number",
        "bank_ids.acc_type",
    )
    def onchange_bmd_fields(self):
        """
        The function `onchange_bmd_fields` sets the fields `bmd_reexport_customer`
        and `bmd_reexport_supplier` to `True` if they are not already set on the changes of certain fields.
        """
        for res in self:
            if not res.bmd_reexport_customer:
                res.bmd_reexport_customer = True
            if not res.bmd_reexport_supplier:
                res.bmd_reexport_supplier = True

    def update_creditor_debtor_number(self):
        self.write(
            {
                "debtor_number": self.env["ir.sequence"]
                .with_company(self.env.company)
                .sudo()
                .next_by_code("res.partner.debtor"),
                "creditor_number": self.env["ir.sequence"]
                .with_company(self.env.company)
                .sudo()
                .next_by_code("res.partner.creditor"),
            }
        )

    @api.model_create_multi
    def create(self, vals_list):
        """To assign the debtor_number or creditor_number"""
        res = super(ResPartner, self).create(vals_list)
        for record in res:
            record.update_creditor_debtor_number()
        return res


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    acc_type = fields.Selection(
        selection=lambda x: x.env["res.partner.bank"].get_supported_account_types(),
        compute="_compute_acc_type",
        store=True,
        string="Acc Type",
    )
