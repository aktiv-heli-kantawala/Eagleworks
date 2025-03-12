from odoo import models, fields
from datetime import datetime, timedelta


class BmdExportHistory(models.Model):
    _name = "bmd.export.history"
    _description = "BMD Export History"
    _rec_name = "report"

    report = fields.Selection(
        string="Report",
        selection=[
            ("customers", "Customers"),
            ("suppliers", "Suppliers"),
            ("general_ledger", "General Ledger"),
            ("bank_moves", "Bank Moves"),
            ("cash_moves", "Cash Moves"),
            ("in_invoices", "In Invoices"),
            ("out_invoices", "Out Invoices"),
            ("export_all", "Export All"),
        ],
        required=True,
        default="export_all",
        copy=False,
    )
    report_type = fields.Selection(
        string="Report Type",
        selection=[("csv", "CSV"), ("xlsx", "XLSX")],
        default="csv",
        required=True,
    )
    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
        required=True,
        readonly=True,
    )
    date_from = fields.Date(
        string="Date From", default=datetime.today() + timedelta(days=-30), copy=False
    )
    date_to = fields.Date(string="Date To", default=datetime.today(), copy=False)
    export_date = fields.Datetime(
        string="Export Date", default=fields.Datetime.now, copy=False
    )
    export_data = fields.Selection(
        string="Export Data",
        selection=[
            ("all_export", "Un-Exported + Re-Export modified data"),
            ("un_exported", "Only Un-Exported"),
            ("export_all", "Force Export All"),
        ],
        default="all_export",
        copy=False,
    )
    fname = fields.Char(string="Fname")
    file_datas = fields.Binary(string="File Datas", copy=False)
    needs_regenerate = fields.Boolean(string="Needs Regenerate", default=True)
    user_id = fields.Many2one(
        "res.users", string="User", default=lambda self: self.env.user, copy=False
    )

    def export_report(self):
        bmd_report = (
            self.env["bmd.reports"]
            .sudo()
            .create(
                {
                    "report": self.report,
                    "report_type": self.report_type,
                    "date_from": self.date_from,
                    "date_to": self.date_to,
                    "export_data": self.export_data,
                    "company_id": self.company_id.id,
                }
            )
        )
        bmd_report.with_context(
            not_create_history=True, history_record=self
        ).export_report()
