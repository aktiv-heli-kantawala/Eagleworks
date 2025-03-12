from markupsafe import Markup
import re

from odoo import api, models, fields


class BaseDocumentLayout(models.TransientModel):
    _inherit = "base.document.layout"

    @api.model
    def _default_report_footer(self):
        # OVERRIDE web/models/base_document_layout
        if self.env.company.external_report_layout_id == self.env.ref(
            "ew_austria_documents.external_layout_eagleworks"
        ):
            company = self.env.company
            # Company VAT should not be present in this footer, as it is displayed elsewhere in the DIN5008 layout
            footer_fields = [
                field
                for field in [company.phone, company.email, company.website]
                if isinstance(field, str) and len(field) > 0
            ]
            return Markup("<br>").join(footer_fields)
        return super()._default_report_footer()

    @api.model
    def _default_company_details(self):
        # OVERRIDE web/models/base_document_layout
        default_company_details = super()._default_company_details()
        if self.env.company.external_report_layout_id == self.env.ref(
            "ew_austria_documents.external_layout_eagleworks"
        ):
            return re.sub(r"(( )*<br>( )*\n)+", r"<br>\n", default_company_details)
        return default_company_details

    hide_header_footer_company = fields.Boolean(
        string="Hide Report EW fields", default=False
    )
    district_court = fields.Char(
        string="District Court", related="company_id.district_court", readonly=True
    )

    @api.onchange("report_layout_id")
    def _onchange_report_layout_id_hide_header_footer_company(self):
        """
        Function to change the flag value which hides and un-hides the
        fields of the module if EW custom layout is chosen.
        """
        if self.report_layout_id == self.env.ref(
            "ew_austria_documents.report_layout_eagleworks"
        ):
            self.hide_header_footer_company = True
            self.paperformat_id = self.env.ref(
                "ew_austria_documents.paperformat_eagleworks_document"
            ).id
        else:
            self.hide_header_footer_company = False
