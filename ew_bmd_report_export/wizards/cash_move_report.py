from odoo import fields, models


class BMDCashMoveReport(models.Model):
    _inherit = "bmd.reports"

    def get_report_data(self, attachments=False):
        """
        Method `get_report_data` retrieves data for a cash moves report and updates certain fields
        in the database accordingly.

        :return: The `result` variable is being returned, which contains the fetched data from the
        database query in the `SELECT` statement.
        """
        if self.report == "cash_moves":
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
                    bmd_exported_cash_move = 't',
                    bmd_reexport_cash_move = 'f'
                WHERE id IN (
                SELECT move.id
                FROM {from_clause}
                WHERE {where_clause}
                )
            """
            self._cr.execute(query2)
            self._cr.commit()

            return result, attachments

        return super(BMDCashMoveReport, self).get_report_data(attachments)

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

        where_clause = super(BMDCashMoveReport, self).moves_where_clause()

        if self.report == "cash_moves":
            where_clause += " AND journal.type = 'cash'"
            if self.export_data == "all_export":
                where_clause += f"""
                    AND (
                        move.bmd_exported_cash_move = false
                        OR move.bmd_exported_cash_move IS NULL
                        OR move.bmd_reexport_cash_move = true
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
                        move.bmd_exported_cash_move = false
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
