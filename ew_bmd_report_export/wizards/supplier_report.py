from odoo import fields, models


class BMDSupplierReport(models.Model):
    _inherit = "bmd.reports"

    def get_report_data(self, attachments=False):
        """
        Method `get_report_data` retrieves data for a supplier report and updates certain fields
        in the database accordingly.

        :return: The `result` variable is being returned, which contains the fetched data from the
        database query in the `SELECT` statement.
        """
        if self.report == "suppliers":
            select_clause = ", ".join(self.contact_select_clause())
            from_clause = self.contact_from_clause()
            where_clause = self.contact_where_clause()

            query = f"""
                SELECT {select_clause}
                FROM {from_clause}
                WHERE {where_clause}
            """
            self._cr.execute(query)
            result = self._cr.fetchall()

            query2 = f"""
                UPDATE res_partner
                SET
                    bmd_exported_supplier = 't',
                    bmd_reexport_supplier = 'f'
                WHERE id IN (
                SELECT partner.id
                FROM {from_clause}
                WHERE {where_clause}
                )
            """
            self._cr.execute(query2)
            self._cr.commit()

            return result, attachments

        return super(BMDSupplierReport, self).get_report_data(attachments)

    def contact_where_clause(self):
        """
        The function `contact_where_clause` generates a SQL WHERE clause based on certain conditions
        including date ranges and supplier export status.

        :return: Returns a SQL WHERE clause based on certain conditions.
        The returned WHERE clause includes filters based on the `report` and `export_data`
        attributes of the object. If the `report` is "suppliers" and the `export_data` is either
        "all_export" or "un_exported", specific conditions are added to the WHERE clause to filter the data
        """
        from_date = (
            self.date_from if self.date_from else fields.Date.today().replace(day=1)
        ).strftime("%Y-%m-%d 00:00:00")
        to_date = (self.date_to if self.date_from else fields.Date.today()).strftime(
            "%Y-%m-%d 23:59:59"
        )

        where_clause = super(BMDSupplierReport, self).contact_where_clause()

        if self.report == "suppliers":
            where_clause += " AND partner.supplier_rank > 0"

            if self.export_data == "all_export":
                where_clause += f"""
                AND (
                    partner.bmd_exported_supplier = false
                    OR partner.bmd_exported_supplier IS NULL
                    OR partner.bmd_reexport_supplier = true
                )
                AND (
                    (partner.create_date >= '{from_date}' AND partner.create_date <= '{to_date}')
                    OR
                    (partner.write_date >= '{from_date}' AND partner.write_date <= '{to_date}')
                )
                """
            elif self.export_data == "un_exported":
                where_clause += f"""
                AND (
                    partner.bmd_exported_supplier = false
                    OR partner.bmd_exported_supplier IS NULL
                )
                AND (
                    partner.create_date >= '{from_date}' AND partner.create_date <= '{to_date}'
                )
                """
            elif self.export_data == "export_all":
                where_clause += f"""
                AND (
                    (partner.create_date >= '{from_date}' AND partner.create_date <= '{to_date}')
                    OR
                    (partner.write_date >= '{from_date}' AND partner.write_date <= '{to_date}')
                )
                """
        return where_clause
