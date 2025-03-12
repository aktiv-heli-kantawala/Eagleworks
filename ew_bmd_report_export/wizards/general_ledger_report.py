from odoo import fields, models


class BMDGeneralLedgerReport(models.Model):
    _inherit = "bmd.reports"

    def get_report_data(self, attachments=False):
        """
        Method `get_report_data` retrieves data for a general ledger report and updates certain
        fields in the database accordingly.

        :return: `result` variable is being returned, which contains the data fetched from the
        database based on the conditions specified in the SQL query for the "general_ledger" report.
        """
        if self.report == "general_ledger":
            select_clause = self.general_ledger_select_clause()
            from_clause = self.general_ledger_from_clause()
            where_clause = self.general_ledger_where_clause()
            group_by_clause = ", ".join(self.general_ledger_group_by_clause())

            query = f"""
                SELECT
                    {select_clause}
                FROM
                    {from_clause}
                WHERE
                    {where_clause}
                GROUP BY
                    {group_by_clause}
            """

            self._cr.execute(query)
            result = self._cr.fetchall()

            query2 = f"""
                UPDATE account_move_line
                SET
                    bmd_exported_general_ledger = 't',
                    bmd_reexport_general_ledger = 'f'
                WHERE id IN (
                SELECT aml.id
                FROM {from_clause}
                WHERE {where_clause}
                )
            """
            self._cr.execute(query2)
            self._cr.commit()

            return result, attachments

        return super(BMDGeneralLedgerReport, self).get_report_data(attachments)

    def general_ledger_select_clause(self):
        """
        Method returns a SQL SELECT clause for retrieving specific fields related to general
        ledger accounts.

        :return: Method returns a formatted SQL SELECT clause that selects various fields
        related to accounts, such as account code, account name, account type, account class,
        VAT tax code, Ust PZ, VAT machine, debit amount, and credit amount.
        The SQL SELECT clause includes multiple CASE statements to determine the account type
        based on certain conditions.
        """
        return f"""
            account.code AS "Account",
            account.name ->> 'en_US' AS "Account Name",
            CASE
                WHEN account.account_type ilike '%asset%' THEN 1
                WHEN account.account_type ilike '%liabilities%' THEN 2
                WHEN account.account_type ilike '%expense%' THEN 3
                WHEN account.account_type ilike '%revenue%' THEN 4
            END AS "Account Type",
            SUBSTRING(account.code FROM 1 FOR 1) AS "Account Class",
            '' AS "VAT tax code",
            (ARRAY_AGG(tax.amount ORDER BY tax.amount DESC) FILTER (
                WHERE tax.amount IS NOT NULL ))[1] AS "Ust PZ",
            1 AS "VAT machine",
            REPLACE(TO_CHAR(ROUND(
                SUM(CASE WHEN aml.debit > 0 THEN aml.debit ELSE 0 END),
                currency.decimal_places
            ), 'FM999999999.00'), '.', ',') AS "Debit",
            REPLACE(TO_CHAR(ROUND(
                SUM(CASE WHEN aml.credit > 0 THEN aml.credit ELSE 0 END),
                currency.decimal_places
            ), 'FM999999999.00'), '.', ',') AS "Credit"
        """

    def general_ledger_from_clause(self):
        """
        Methods returns a SQL FROM clause for a general ledger report query.

        :return: `general_ledger_from_clause` method returns a SQL query string that includes
        multiple JOIN statements to retrieve data from various tables related to accounting
        transactions.
        The query selects data from tables such as `account_move_line`, `account_account`,
        `account_move_line_account_tax_rel`, `account_tax`, `account_move`, `res_company`, and
        `res_currency` by joining them based on their relationships.
        """
        return """
            account_move_line aml
            LEFT JOIN account_account account ON account.id = aml.account_id
            LEFT JOIN account_move_line_account_tax_rel tax_rel ON aml.id = tax_rel.account_move_line_id
            LEFT JOIN account_tax tax ON tax_rel.account_tax_id = tax.id
            JOIN account_move move ON move.id = aml.move_id
            JOIN res_company company ON company.id = move.company_id
            JOIN res_currency currency ON currency.id = company.currency_id
        """

    def general_ledger_where_clause(self):
        """
        Method `general_ledger_where_clause` generates a WHERE clause for filtering general ledger
        data based on certain conditions.

        :return: The function `general_ledger_where_clause` returns a SQL WHERE clause based on certain
        conditions. The returned WHERE clause includes filters for `display_type`, `company_id`,
        `parent_state`, and additional conditions based on the `export_data` attribute of the object.
        """

        from_date = (
            self.date_from if self.date_from else fields.Date.today().replace(day=1)
        ).strftime("%Y-%m-%d 00:00:00")
        to_date = (self.date_to if self.date_from else fields.Date.today()).strftime(
            "%Y-%m-%d 23:59:59"
        )

        where_clause = f"""
            (
                aml.display_type NOT IN ('line_section', 'line_note')
                OR aml.display_type IS NULL
            )
            AND aml.company_id = {self.company_id.id}
            AND aml.parent_state = 'posted'
        """

        if self.export_data == "all_export":
            where_clause += f"""
            AND (
                aml.bmd_exported_general_ledger = false
                OR aml.bmd_exported_general_ledger IS NULL
                OR aml.bmd_reexport_general_ledger = true
            )
            AND (
                (aml.create_date >= '{from_date}' AND aml.create_date <= '{to_date}')
                OR
                (aml.write_date >= '{from_date}' AND aml.write_date <= '{to_date}')
            )
            """
        elif self.export_data == "un_exported":
            where_clause += f"""
                AND (
                    aml.bmd_exported_general_ledger = false
                    OR aml.bmd_exported_general_ledger IS NULL
                )
                AND (
                    aml.create_date >= '{from_date}' AND aml.create_date <= '{to_date}'
                )
                """
        elif self.export_data == "export_all":
            where_clause += f"""
                    AND (
                       (aml.create_date >= '{from_date}' AND aml.create_date <= '{to_date}')
                       OR
                       (aml.write_date >= '{from_date}' AND aml.write_date <= '{to_date}')
                    )
                """
        return where_clause

    def general_ledger_group_by_clause(self):
        """
        Method `general_ledger_group_by_clause` returns a list of fields to group by in a general
        ledger report.

        :return: Method is returning a list of strings that represent the fields to be used in a
        GROUP BY clause for a general ledger query.
        The returned list includes "account.code", "account.name", "account.account_type", and
        "currency.decimal_places".
        """
        return [
            "account.code",
            "account.name",
            "account.account_type",
            "currency.decimal_places",
        ]
