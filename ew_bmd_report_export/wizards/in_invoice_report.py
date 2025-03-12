from odoo import fields, models

from .bmd_reports import REPORT_HEADERS


class BMDInInvoiceReport(models.Model):
    _inherit = "bmd.reports"

    def in_invoice_group_by_clause(self):
        """
        Method `in_invoice_group_by_clause` returns a list of fields to group by in a general
        ledger report.

        :return: Method is returning a list of strings that represent the fields to be used in a
        GROUP BY clause for a general ledger query.
        The returned list includes "account.code", "account.name", "account.account_type", and
        "currency.decimal_places".
        """
        return [
            "account.code",
            "move.date",
            "journal.code",
            "tax.amount",
            "partner.debtor_number",
            "partner.creditor_number",
            "invoice.invoice_date",
            "invoice.name",
            "move.price_unit",
            "move.display_type",
            "rc.name",
            "tax.bmd_steuercode",
        ]

    def in_invoice_order_by_clause(self):
        return """invoice.invoice_date"""

    def get_report_data(self, attachments=False):
        """
        Method `get_report_data` retrieves data for a In Invoice report and updates certain fields
        in the database accordingly.

        :return: The `result` variable is being returned, which contains the fetched data from the
        database query in the `SELECT` statement.
        """
        if self.report == "in_invoices":
            select_clause = ", ".join(self.moves_select_clause())
            from_clause = self.moves_from_clause()
            where_clause = self.moves_where_clause()
            group_by_clause = ", ".join(self.in_invoice_group_by_clause())
            order_by_clause = "".join(self.in_invoice_order_by_clause())
            attach_query = f"""select attachment.id from account_move_line move left join account_move invoice ON move.move_id = invoice.id LEFT JOIN account_account account ON move.account_id = account.id left join account_journal journal ON invoice.journal_id = journal.id left join ir_attachment attachment ON attachment.res_id = invoice.id AND attachment.res_model = 'account.move' WHERE {where_clause}"""
            self._cr.execute(attach_query)
            attachments = self._cr.fetchall()

            query = f"""
                SELECT {select_clause}
                FROM {from_clause}
                WHERE {where_clause}
                GROUP BY
                    {group_by_clause}
                ORDER BY
                    {order_by_clause}
            """
            self._cr.execute(query)
            result = self._cr.fetchall()
            query2 = f"""
                UPDATE account_move_line
                SET
                    bmd_exported_in_move = 't',
                    bmd_reexport_in_move = 'f'
                WHERE id IN (
                SELECT move.id
                FROM {from_clause}
                WHERE {where_clause}
                )
            """
            self._cr.execute(query2)
            self._cr.commit()
            if result:
                return result, set(
                    tuple for tuple in attachments if tuple[0] is not None
                )
            return result, attachments
        return super(BMDInInvoiceReport, self).get_report_data(attachments)

    def moves_where_clause(self):
        """
        The function `moves_where_clause` generates a SQL WHERE clause based on certain conditions
        including date ranges and move export status.

        :return: Returns a SQL WHERE clause based on certain conditions.
        The returned WHERE clause includes filters based on the `report` and `export_data`
        attributes of the object. If the `report` is "bank or cash or in or out" and the `export_data` is either
        "all_export" or "un_exported", specific conditions are added to the WHERE clause to filter the data
        """
        from_date = (
            self.date_from if self.date_from else fields.Date.today().replace(day=1)
        ).strftime("%Y-%m-%d 00:00:00")
        to_date = (self.date_to if self.date_from else fields.Date.today()).strftime(
            "%Y-%m-%d 23:59:59"
        )

        where_clause = super(BMDInInvoiceReport, self).moves_where_clause()

        if self.report == "in_invoices":
            where_clause += " AND journal.type = 'purchase'"
            if self.export_data == "all_export":
                where_clause += f"""
                    AND (
                        move.bmd_exported_in_move = false
                        OR move.bmd_exported_in_move IS NULL
                        OR move.bmd_reexport_in_move = true
                    )
                    AND (
                        (move.invoice_date >= '{from_date}' AND move.invoice_date <= '{to_date}')
                    )
                    AND move.display_type = 'product'
                """
            elif self.export_data == "un_exported":
                where_clause += f"""
                    AND (
                        move.bmd_exported_in_move = false
                    )
                    AND (
                        move.invoice_date >= '{from_date}' AND move.invoice_date <= '{to_date}'
                    )
                    AND move.display_type = 'product' 
                """
            elif self.export_data == "export_all":
                where_clause += f"""
                    AND (
                       (move.invoice_date >= '{from_date}' AND move.invoice_date <= '{to_date}')
                    )
                    AND move.display_type = 'product'
                """
        return where_clause

    def moves_from_clause(self):
        """
        Method returns a SQL FROM clause for a moves table with additional joins.

        :return: A SQL FROM clause is being returned, specifying the tables and aliases to be used in a
        query. The tables included are 'account_move_line' aliased as 'move', 'account_journal' aliased as
        'journal', and 'account_account' aliased as 'account', 'account_tax' aliased as 'tax'.
        """
        res = super(BMDInInvoiceReport, self).moves_from_clause()
        if self.report == "in_invoices":
            res += """LEFT JOIN res_partner partner ON move.partner_id = partner.id 
                    LEFT JOIN account_move invoice ON move.move_id = invoice.id
                    LEFT JOIN res_currency rc ON move.currency_id = rc.id
                    LEFT JOIN (SELECT DISTINCT ON (res_id) id, res_id, name FROM ir_attachment WHERE res_model = 'account.move' ORDER BY res_id, id DESC) AS attachment ON attachment.res_id = invoice.id
                """
        return res

    def moves_select_clause(self):
        """
        Generic method `moves_select_clause` generates a list of SQL select clauses based on specified
        headers for a report.


        :return: The `moves_select_clause` method returns a list of SQL select clauses based on the
        headers specified in the `REPORT_HEADERS` dictionary for a given report.
        Each header corresponds to a specific field in the database schema related to moves.
        The method constructs SQL select clauses for each header, mapping the database fields to user-friendly column names
        for reporting purposes.
        """
        if self.report == "in_invoices":
            creditor_number = """ partner.creditor_number AS "Offset account" """
            text = """ COALESCE((ARRAY_AGG(move.name ORDER BY move.id))[1], '') AS "text" """
            steuer = """ 
                        REPLACE(TO_CHAR(
                            COALESCE(SUM(move.price_subtotal * (tax.amount / 100)), 0), 
                            'FM9999999990.00'
                        ), '.', ',') AS "tax" """
            betrag = """ REPLACE(TO_CHAR(SUM(move.price_subtotal), 'FM999999999.00'), '.', ',') AS "amount" """
            buchcode = """ 
                       CASE 
                           WHEN SUM(CASE WHEN move.debit > 0 THEN 1 ELSE 0 END) > 0 THEN '2' 
                           WHEN SUM(CASE WHEN move.credit > 0 THEN 1 ELSE 0 END) > 0 THEN '1' 
                           ELSE '' 
                       END AS "posting code" """
            document = """ COALESCE((ARRAY_AGG(attachment.name ORDER BY attachment.id DESC))[1], '') AS "attachments" """
            select_clause = []
            header_mapping = {
                "satzart": """ '0' AS "record type" """,
                "konto": creditor_number,
                "gkonto": """ account.code AS "Account" """,
                "belegnr": """ invoice.name AS "document number" """,
                "belegdatum": """ TO_CHAR(invoice.invoice_date, 'DD.MM.YYYY') AS "document date" """,
                "buchsymbol": """ journal.code AS "book symbol" """,
                "wae": """ rc.name AS "Currency Code" """,
                "buchcode": buchcode,
                "prozent": """ tax.amount AS "percent" """,
                "steuercode": """ tax.bmd_steuercode AS "tax code" """,
                "betrag": betrag,
                "steuer": steuer,
                "text": text,
            }
            for header in REPORT_HEADERS[self.report]:
                # Bank and In and Out header
                if header == "kost":
                    header_mapping.update({"kost": """ '' AS "cost" """})
                # Bank and In header
                if header == "filiale":
                    header_mapping.update({"filiale": """ '' AS "branch" """})
                header_mapping.update({"dokument": document})
                select_clause.append(header_mapping.get(header, ""))
            return select_clause
        else:
            return super().moves_select_clause()
