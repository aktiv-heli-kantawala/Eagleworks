from odoo import fields, models

from .bmd_reports import REPORT_HEADERS


class BMDBankMoveReport(models.Model):
    _inherit = "bmd.reports"

    def get_report_data(self, attachments=False):
        """
        Method `get_report_data` retrieves data for a bank moves report and updates certain fields
        in the database accordingly.

        :return: The `result` variable is being returned, which contains the fetched data from the
        database query in the `SELECT` statement.
        """
        if self.report == "bank_moves":
            select_clause = ", ".join(self.moves_select_clause())
            from_clause = self.moves_from_clause()
            where_clause = self.moves_where_clause()
            query = f"""
                SELECT {select_clause}
                FROM {from_clause}
                WHERE {where_clause}
            """
            self._cr.execute(query)
            result = self._cr.fetchall()

            query2 = f"""
                UPDATE account_move_line
                SET
                    bmd_exported_bank_move = 't',
                    bmd_reexport_bank_move = 'f'
                WHERE id IN (
                SELECT move.id
                FROM {from_clause}
                WHERE {where_clause}
                )
            """
            self._cr.execute(query2)
            self._cr.commit()
            return result, attachments

        return super(BMDBankMoveReport, self).get_report_data(attachments)

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
        select_clause = []
        header_mapping = {
            "satzart": """ '' AS "record type" """,
            "konto": """ account.code AS "Account" """,
            "gkonto": """ '' AS "Offset account" """,
            "belegnr": """ '' AS "document number" """,
            "belegdatum": """ TO_CHAR(move.date, 'DD.MM.YYYY') AS "document date" """,
            "buchsymbol": """ journal.code AS "book symbol" """,
            "buchcode": """ CASE WHEN move.debit > 0 THEN '1' WHEN move.credit > 0 THEN '2' ELSE '' END AS "posting code" """,
            "prozent": """ tax.amount AS "percent" """,
            "steuercode": """ tax.bmd_steuercode AS "tax code" """,
            "betrag": """ CASE WHEN move.debit > 0 THEN REPLACE(TO_CHAR(move.debit, 'FM999999999.00'), '.', ',') WHEN move.credit > 0 THEN  REPLACE(TO_CHAR(move.credit, 'FM999999999.00'), '.', ',') END AS "amount" """,
            "steuer": """ CASE WHEN move.debit > 0 THEN REPLACE(TO_CHAR(move.debit * (tax.amount / 100), 'FM999999999.00'), '.', ',') WHEN move.credit > 0 THEN  REPLACE(TO_CHAR(move.credit * (tax.amount / 100), 'FM999999999.00'), '.', ',') END AS "tax" """,
            "text": """ move.name AS "text" """,
        }
        for header in REPORT_HEADERS[self.report]:
            # Bank and In and Out header
            if header == "kost":
                header_mapping.update({"kost": """ '' AS "cost" """})
            # Bank and In header
            if header == "filiale":
                header_mapping.update({"filiale": """ '' AS "branch" """})
            # Cash header
            if header == "skonto":
                header_mapping.update(
                    {"skonto": """ move.discount AS "cash discount" """}
                )
            select_clause.append(header_mapping.get(header, ""))
        return select_clause

    def moves_from_clause(self):
        """
        Method returns a SQL FROM clause for a moves table with additional joins.

        :return: A SQL FROM clause is being returned, specifying the tables and aliases to be used in a
        query. The tables included are 'account_move_line' aliased as 'move', 'account_journal' aliased as
        'journal', and 'account_account' aliased as 'account', 'account_tax' aliased as 'tax'.
        """
        return """
                    account_move_line move 
                    LEFT JOIN account_account account ON move.account_id = account.id
                    LEFT JOIN account_journal journal ON move.journal_id = journal.id
                    LEFT JOIN account_move_line_account_tax_rel rel ON move.id = rel.account_move_line_id LEFT JOIN account_tax tax ON rel.account_tax_id = tax.id
                """

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

        where_clause = (
            f"(move.company_id = {self.company_id.id} OR move.company_id IS NULL)"
        )

        if self.report == "bank_moves":
            where_clause += " AND journal.type = 'bank'"
            if self.export_data == "all_export":
                where_clause += f"""
                    AND (
                        move.bmd_exported_bank_move = false
                        OR move.bmd_exported_bank_move IS NULL
                        OR move.bmd_reexport_bank_move = true
                    )
                    AND (
                       (move.create_date >= '{from_date}' AND move.create_date <= '{to_date}')
                       OR
                       (move.write_date >= '{from_date}' AND move.write_date <= '{to_date}')
                    )
                """
            elif self.export_data == "un_exported":
                where_clause += f"""
                    AND (
                        move.bmd_exported_bank_move = false
                    )
                    AND (
                        move.create_date >= '{from_date}' AND move.create_date <= '{to_date}'
                    )
                """
            elif self.export_data == "export_all":
                where_clause += f"""
                    AND (
                       (move.create_date >= '{from_date}' AND move.create_date <= '{to_date}')
                       OR
                       (move.write_date >= '{from_date}' AND move.write_date <= '{to_date}')
                    )
                """
        return where_clause
