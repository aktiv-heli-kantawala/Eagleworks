import base64
import csv
import io
import zipfile
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import xlsxwriter

REPORT_HEADERS = {
    "customers": [
        "Konto-Nr",
        "Nachname",
        "Vorname",
        "Titel",
        "Beruf",
        "Straße",
        "PLZ",
        "Ort",
        "Land",
        "UID-Nummer",
        "E-Mail",
        "Homepage",
        "Telefon nummer",
        "IBAN",
        "Zahlungsziel",
        "Skonto%",
        "Skontotage",
        "Freifeld 10",
    ],
    "suppliers": [
        "Konto-Nr",
        "Nachname",
        "Straße",
        "PLZ",
        "Ort",
        "Land",
        "UID-Nummer",
        "E-Mail",
        "Homepage",
        "Telefon nummer",
        "IBAN",
        "Zahlungsziel",
        "Skonto%",
        "Skontotage",
        "Freifeld 10",
    ],
    "general_ledger": [
        "Konto",
        "Bezeichnung",
        "Kontoart",
        "Kontoklasse",
        "USt Steuercode",
        "Ust PZ",
        "USt Automat",
        "Soll",
        "Haben",
    ],
    "bank_moves": [
        "satzart",
        "konto",
        "gkonto",
        "belegnr",
        "belegdatum",
        "buchsymbol",
        "buchcode",
        "prozent",
        "steuercode",
        "betrag",
        "steuer",
        "text",
        "kost",
        "filiale",
    ],
    "cash_moves": [
        "satzart",
        "konto",
        "gkonto",
        "belegnr",
        "belegdatum",
        "buchsymbol",
        "buchcode",
        "prozent",
        "steuercode",
        "betrag",
        "steuer",
        "text",
        "skonto",
    ],
    "in_invoices": [
        "satzart",
        "konto",
        "gkonto",
        "belegnr",
        "belegdatum",
        "buchsymbol",
        "wae",
        "buchcode",
        "prozent",
        "steuercode",
        "betrag",
        "steuer",
        "text",
        "kost",
        "filiale",
        "dokument",
    ],
    "out_invoices": [
        "satzart",
        "konto",
        "gkonto",
        "belegnr",
        "belegdatum",
        "buchsymbol",
        "wae",
        "buchcode",
        "prozent",
        "steuercode",
        "betrag",
        "steuer",
        "text",
        "kost",
        "extbelegnr",
        "dokument",
    ],
}


class BMDReport(models.Model):
    _name = "bmd.reports"
    _description = "Export BMD Report"

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
        default=lambda self: self.env.company,
        required=True,
    )
    date_from = fields.Date(
        default=datetime.today() + timedelta(days=-30), copy=False, string="Date From"
    )
    date_to = fields.Date(default=datetime.today(), copy=False, string="Date To")
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
    file_datas = fields.Binary(copy=False, string="File Datas")
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        domain=[("res_model", "=", "bmd.reports")],
        string="Attachments",
        readonly=True,
    )
    needs_regenerate = fields.Boolean(default=True, string="Needs Regenerate")

    @api.onchange(
        "report",
        "report_type",
        "company_id",
        "date_from",
        "date_to",
        "export_data",
    )
    def onchange_report(self):
        self.needs_regenerate = True
        self.attachment_ids = False

    def _export_report(self):
        """
        Generic method `_export_report` generates a report in either CSV or XLSX format and directly return it for download

        :return: The `_export_report` method returns a dictionary with keys "type", "url", and "target" to download the file directly.
        """
        from_date = (
            self.date_from if self.date_from else fields.Date.today().replace(day=1)
        ).strftime("%Y-%m-%d")
        to_date = (self.date_to if self.date_from else fields.Date.today()).strftime(
            "%Y-%m-%d"
        )

        FILENAME = "_".join([W.capitalize() for W in self.report.split("_")])
        FILENAME += "_" + from_date + "_to_" + to_date

        if self.env.user.has_group("base.group_multi_company"):
            FILENAME += "_" + self.company_id.name

        datas = False
        DATA = self.get_report_data(attachments=False)  # Get report data
        if not DATA[0]:
            return False

        if self.report_type == "csv":
            FILENAME += ".csv"
            data = io.StringIO()
            writer = csv.writer(data, delimiter=",")

            # Write header part - csv
            self.write_headers(writer)

            # Write report data - csv
            self.write_data(writer, DATA[0])

            # Generate csv file
            datas = base64.encodebytes(data.getvalue().encode("utf-8"))

        elif self.report_type == "xlsx":
            FILENAME += ".xlsx"
            fp = io.BytesIO()
            workbook = xlsxwriter.Workbook(fp, {"in_memory": True})
            worksheet = workbook.add_worksheet(self.report)

            # Write header part - xlsx
            self.write_headers(worksheet)
            # Write report data - xlsx
            self.write_data(worksheet, DATA[0])

            # Generate xlsx file
            workbook.close()
            datas = base64.encodebytes(fp.getvalue())

        if datas:
            self.write({"file_datas": datas})
            created_history = self._context.get("history_record", False)
            if not self._context.get("not_create_history", False):
                created_history = self.create_history_bmd_export(datas, FILENAME)
            if created_history:
                created_history.write(
                    {
                        "file_datas": datas,
                        "fname": FILENAME,
                    }
                )
            return (
                {"name": FILENAME, "datas": datas},
                {"attachments": DATA[1] or False},
                created_history,
            )

    def write_headers(self, writer):
        """
        Generic method `write_headers` writes headers to a CSV writer or an Excel worksheet based on the
        report type.

        :param writer: The `writer` parameter in the `write_headers` method is used to write headers to
        either a CSV file or an Excel file (XLSX). Depending on the `report_type`, the method writes the
        headers in different ways:
        """
        headers = REPORT_HEADERS.get(self.report)
        if self.report_type == "csv":
            writer.writerow(headers)

        elif self.report_type == "xlsx":
            # Here the writer is worksheet
            for column, header in enumerate(headers):
                writer.write(0, column, header)

    def write_data(self, writer, report_lines):
        """
        The function `write_data` writes data to a file in either CSV or XLSX format based on the
        specified report type.

        :param writer: The `writer` parameter in the `write_data` method is used to write data to a
        file. Depending on the `report_type`, the method writes the `report_lines` data either to a CSV
        file or an Excel file
        :param report_lines: `report_lines` is a list of lists where each inner list represents a row of
        data to be written to the output file. Each element in the inner list corresponds to a cell
        value in that row. The structure of `report_lines` should be like this:
        """
        # `data` should be in the the format: [[],[],..]
        if self.report_type == "csv":
            writer.writerows(report_lines)

        elif self.report_type == "xlsx":
            # Here the writer is worksheet
            for row, line in enumerate(report_lines, start=1):
                for column, val in enumerate(line):
                    writer.write(row, column, val)

    def get_report_data(self, attachments=False):
        """
        Generic function `get_report_data` should be inherited to have the report data for verious reports.
        the report data should be in the format of list of list.
        :return: An list of row data which should be a list `[]` is being returned.
        """
        if self.report == "export_all":
            raise ValidationError(_("'Export All' feature is pending to develop"))
        else:
            return []

    def export_report(self):
        """
        Generates attachments for each report selected on the form and adds them to the form for downloading.
        """
        attachment = self.env["ir.attachment"]
        self.attachment_ids = False
        # Determine date range
        from_date = (
            self.date_from if self.date_from else fields.Date.today().replace(day=1)
        ).strftime("%Y-%m-%d")
        to_date = (self.date_to if self.date_from else fields.Date.today()).strftime(
            "%Y-%m-%d"
        )

        # Get report names
        report_name = {
            key: value
            for key, value in self._fields["report"]._description_selection(self.env)
        }
        reports_with_no_data = []
        in_filename, out_filename = False, False
        if self.report == "export_all":
            reports, in_zip_attachments, out_zip_attachments = [], [], []
            created_history = False
            for report in dict(self._fields["report"].selection).keys():
                if report != "export_all":
                    new_report = self.copy(
                        {
                            "report": report,
                            "report_type": self.report_type,
                            "date_from": self.date_from,
                            "date_to": self.date_to,
                            "export_data": self.export_data,
                            "company_id": self.company_id.id,
                        }
                    )

                    val = new_report._export_report()
                    if val:
                        created_history = val[2]
                        # Prepare attachments list and define file name
                        attachments = val[1].get("attachments")
                        if attachments and attachments != {(None,)}:
                            if report == "in_invoices":
                                in_zip_attachments.append(attachments)
                                in_filename = (
                                    f"in-invoices-pdf_{from_date}_to_{to_date}.zip"
                                )
                            elif report == "out_invoices":
                                out_zip_attachments.append(attachments)
                                out_filename = (
                                    f"out-invoices-pdf_{from_date}_to_{to_date}.zip"
                                )
                        val[0].update({"res_id": self.id, "res_model": "bmd.reports"})
                        reports.append(val[0])
                    else:
                        reports_with_no_data.append(report_name.get(report, ""))
            if reports:
                attachments = attachment.create(reports)
                # FILENAME
                FILENAME = "all_reports"
                FILENAME += "_" + from_date + "_to_" + to_date
                if self.env.user.has_group("base.group_multi_company"):
                    FILENAME += "_" + self.company_id.name
                buffer = io.BytesIO()
                if not (in_zip_attachments and out_zip_attachments):
                    # All reports zip
                    with zipfile.ZipFile(
                        buffer, "w", compression=zipfile.ZIP_DEFLATED
                    ) as zipfile_obj:
                        for attachment in attachments:
                            zipfile_obj.writestr(
                                attachment.display_name, attachment.raw
                            )
                    zip = buffer.getvalue()
                    zipDatas = base64.encodebytes(zip)
                    self.write({"file_datas": zipDatas})
                    Url = (
                        "web/content/?model=bmd.reports&download=true&field=file_datas&id=%s&filename=%s"
                        % (self.id, FILENAME)
                    )
                else:
                    in_zip_att = False
                    out_zip_att = False
                    zipDatas_att = False
                    if out_zip_attachments:
                        # attachment zip for out invoices
                        with zipfile.ZipFile(
                            buffer, "w", compression=zipfile.ZIP_DEFLATED
                        ) as zipfile_obj:
                            out_zip_atta = [
                                attachment
                                for attachment in out_zip_attachments
                                if attachment
                            ]
                            attachment_ids = [
                                id for attachment in out_zip_atta for id in attachment
                            ]
                            for attachment in attachment_ids:
                                if attachment:
                                    attachment = self.env["ir.attachment"].browse(
                                        attachment
                                    )
                                    zipfile_obj.writestr(
                                        attachment.name,
                                        base64.b64decode(attachment.datas),
                                    )
                        out_zip_att = buffer.getvalue()
                        zipDatas_att = base64.encodebytes(out_zip_att)
                        self.write({"file_datas": zipDatas_att})
                    # attachment  zip for in invoices
                    if in_zip_attachments:
                        with zipfile.ZipFile(
                            buffer, "w", compression=zipfile.ZIP_DEFLATED
                        ) as zipfile_obj:
                            in_zip_atta = [
                                attachment
                                for attachment in in_zip_attachments
                                if attachment
                            ]
                            attachment_ids = [
                                id for attachment in in_zip_atta for id in attachment
                            ]
                            for attachment in attachment_ids:
                                if attachment:
                                    attachment = self.env["ir.attachment"].browse(
                                        attachment
                                    )
                                    zipfile_obj.writestr(
                                        attachment.name,
                                        base64.b64decode(attachment.datas),
                                    )
                        in_zip_att = buffer.getvalue()
                        zipDatas_att = base64.encodebytes(in_zip_att)
                        self.write({"file_datas": zipDatas_att})
                    # Create zip with attachments zip
                    # All reports zip
                    with zipfile.ZipFile(
                        buffer, "w", compression=zipfile.ZIP_DEFLATED
                    ) as zipfile_obj:
                        for attachment in attachments:
                            zipfile_obj.writestr(
                                attachment.display_name, attachment.raw
                            )
                        zipfile_obj.writestr(in_filename, in_zip_att)
                        zipfile_obj.writestr(out_filename, out_zip_att)
                    zip = buffer.getvalue()
                    zipDatas = base64.encodebytes(zip)
                    self.write({"file_datas": zipDatas})

                    Url = (
                        "web/content/?model=bmd.reports&download=true&field=file_datas&id=%s&filename=%s"
                        % (self.id, FILENAME)
                    )
                # Create history
                if zipDatas and created_history:
                    created_history.write(
                        {
                            "file_datas": zipDatas,
                            "fname": FILENAME,
                        }
                    )
                elif zipDatas_att and created_history:
                    created_history.write(
                        {
                            "file_datas": zipDatas_att,
                            "fname": FILENAME,
                        }
                    )
                return {
                    "type": "ir.actions.act_url",
                    "url": Url,
                    "target": "new",
                }
        else:
            report = self._export_report()
            out_file, in_file = False, False
            if report:
                created_history = report[2]
                report[0].update({"res_id": self.id, "res_model": "bmd.reports"})
                attachment.create(report[0])
                zipDatas_att = False
                zipDatas = False
                # Create ZIP for attachments
                if report[1].get("attachments"):

                    buffer = io.BytesIO()
                    with zipfile.ZipFile(
                        buffer, "w", compression=zipfile.ZIP_DEFLATED
                    ) as zipfile_obj:
                        for attachment in report[1].get("attachments"):
                            attachment = self.env["ir.attachment"].browse(attachment)
                            zipfile_obj.writestr(
                                attachment.name,
                                base64.b64decode(attachment.datas),
                            )
                    zip_att = buffer.getvalue()
                    zipDatas_att = base64.encodebytes(zip_att)
                    self.write({"file_datas": zipDatas_att})
                    out_filename, in_filename = False, False
                    if self.report == "out_invoices":
                        out_filename = (
                            "out-invoices-pdf_" + from_date + "_to_" + to_date + ".zip"
                        )
                        out_file = (
                            "out_invoices_" + from_date + "_to_" + to_date + ".zip"
                        )
                    elif self.report == "in_invoices":
                        in_filename = (
                            "in-invoices-pdf_" + from_date + "_to_" + to_date + ".zip"
                        )
                        in_file = "in_invoices_" + from_date + "_to_" + to_date + ".zip"
                    # Create zip for attachment zip and csv
                    with zipfile.ZipFile(
                        buffer, "w", compression=zipfile.ZIP_DEFLATED
                    ) as zipfile_obj:
                        zipfile_obj.writestr(in_filename or out_filename, zip_att)
                        zipfile_obj.writestr(
                            report[0].get("name", ""),
                            base64.b64decode(report[0].get("datas", "")),
                        )
                    zip = buffer.getvalue()
                    zipDatas = base64.encodebytes(zip)
                    self.write({"file_datas": zipDatas})

                    Url = (
                        "web/content/?model=bmd.reports&download=true&field=file_datas&id=%s&filename=%s"
                        % (self.id, out_file or in_file)
                    )
                else:
                    Url = (
                        "web/content/?model=bmd.reports&download=true&field=file_datas&id=%s&filename=%s"
                        % (self.id, report[0].get("name", ""))
                    )
                # Create history
                if zipDatas and created_history:
                    created_history.write(
                        {
                            "file_datas": zipDatas,
                            "fname": out_file or in_file,
                        }
                    )
                elif zipDatas_att and created_history:
                    created_history.write(
                        {
                            "file_datas": zipDatas_att,
                            "fname": out_file or in_file,
                        }
                    )
                # DOWMLOAD URL
                return {
                    "type": "ir.actions.act_url",
                    "url": Url,
                    "target": "new",
                }
            else:
                reports_with_no_data.append(report_name.get(self.report, ""))
        if reports_with_no_data:
            msg = "No data found to export for the report:"
            for res in reports_with_no_data:
                msg += " %s," % res
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "sticky": True,
                    "message": msg,
                },
            }
        self.needs_regenerate = False

        return dict(
            name="Export - BMD Reports",
            view_mode="form",
            res_id=self.id,
            res_model="bmd.reports",
            view_type="form",
            type="ir.actions.act_window",
            target="new",
        )

    def create_history_bmd_export(self, zipDatas, FILENAME):
        return self.env["bmd.export.history"].create(
            {
                "report": self.report,
                "report_type": self.report_type,
                "export_data": self.export_data,
                "date_from": self.date_from,
                "date_to": self.date_to,
                "file_datas": zipDatas,
                "fname": FILENAME,
            }
        )

    def close(self):
        self.env["ir.attachment"].search(
            [("res_model", "=", "bmd.reports"), ("res_id", "=", self.id)]
        ).unlink()
