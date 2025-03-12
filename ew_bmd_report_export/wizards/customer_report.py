from odoo import fields, models


from .bmd_reports import REPORT_HEADERS


class BMDCustomerReport(models.Model):
    _inherit = "bmd.reports"

    def get_report_data(self, attachments=False):
        """
        The method `get_report_data` retrieves data for a customer report and updates the
        `bmd_exported_customer` and `bmd_reexport_customer` fields in the `res_partner` table.
        :return: The `result` variable is being returned, which contains the fetched data from the
        database query with will be in the format [[], [],...].
        """
        if self.report == "customers":
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
                    bmd_exported_customer = 't',
                    bmd_reexport_customer = 'f'
                WHERE id IN (
                SELECT partner.id
                FROM {from_clause}
                WHERE {where_clause}
                )
            """
            self._cr.execute(query2)
            self._cr.commit()

            return result, attachments

        return super(BMDCustomerReport, self).get_report_data(attachments)

    def contact_select_clause(self):
        """
        Generic method `contact_select_clause` generates a list of SQL select clauses based on specified
        headers for a report.

        :return: The `contact_select_clause` method returns a list of SQL select clauses based on the
        headers specified in the `REPORT_HEADERS` dictionary for a given report.
        Each header corresponds to a specific field in the database schema related to a partner/contact.
        The method constructs SQL select clauses for each header, mapping the database fields to user-friendly column names
        for reporting purposes.
        """
        select_clause = []
        for header in REPORT_HEADERS[self.report]:
            if self.report == "suppliers":
                if header == "Konto-Nr":
                    select_clause.append(
                        """ partner.creditor_number AS "Account Number" """
                    )
            else:
                if header == "Konto-Nr":
                    select_clause.append(
                        """ partner.debtor_number AS "Account Number" """
                    )
            if header == "Nachname":
                select_clause.append(""" partner.name AS "Last Name" """)
            if header == "Vorname":
                select_clause.append(""" '' AS "First Name" """)
            if header == "Titel":
                select_clause.append(""" partner.title AS "Title" """)
            if header == "Beruf":
                select_clause.append(""" partner.function AS "Occupation" """)
            if header == "Straße":
                select_clause.append(
                    """
                    CASE
                        WHEN partner.street2 IS NOT NULL THEN partner.street || ', ' || partner.street2
                        ELSE partner.street
                    END AS "Street"
                """
                )
            if header == "PLZ":
                select_clause.append(""" partner.zip AS "Zip Code" """)
            if header == "Ort":
                select_clause.append(""" partner.city AS "City" """)
            if header == "Land":
                select_clause.append(""" country.code AS "Country" """)
            if header == "UID-Nummer":
                select_clause.append(""" partner.vat AS "UID number" """)
            if header == "E-Mail":
                select_clause.append(""" partner.email AS "Email" """)
            if header == "Homepage":
                select_clause.append(""" partner.website AS "Homepage" """)
            if header == "Telefon nummer":
                select_clause.append(""" partner.phone AS "Telephone number" """)
            if header == "IBAN":
                select_clause.append(
                    """ COALESCE(partner_bank.acc_number, '') AS "IBAN" """
                )
            if header == "Zahlungsziel":
                select_clause.append(""" '' AS "Payment due date" """)
            if header == "Skonto%":
                select_clause.append(""" '' AS "Discount%" """)
            if header == "Skontotage":
                select_clause.append(""" '' AS "Discount days" """)
            if header == "Freifeld 10":
                select_clause.append(""" '' AS "Free field 10" """)

        return select_clause

    def contact_from_clause(self):
        """
        Method returns a SQL FROM clause for a contact table with additional joins.

        :return: A SQL FROM clause is being returned, specifying the tables and aliases to be used in a
        query. The tables included are 'res_partner' aliased as 'partner', 'res_partner_bank' aliased as
        'partner_bank', and 'res_country' aliased as 'country'. The JOIN conditions are also specified
        for the 'res_partner_bank' and 'res_country' tables.
        """
        return """
            res_partner partner
            LEFT JOIN res_partner_bank partner_bank ON partner_bank.partner_id = partner.id AND partner_bank.acc_type = 'iban'
            LEFT JOIN res_country country ON partner.country_id = country.id
        """

    def contact_where_clause(self):
        """
        Method `contact_where_clause` generates a WHERE clause for SQL queries based on certain
        conditions related to dates and partner attributes.

        :return: The `contact_where_clause` method returns a SQL WHERE clause based on the conditions
        set by the attributes of the object (`self`). The WHERE clause includes conditions related to
        the company ID, report type, and export data options selected. The final WHERE clause is
        constructed based on these conditions and is returned as a string.
        """
        from_date = (
            self.date_from if self.date_from else fields.Date.today().replace(day=1)
        ).strftime("%Y-%m-%d 00:00:00")
        to_date = (self.date_to if self.date_from else fields.Date.today()).strftime(
            "%Y-%m-%d 23:59:59"
        )

        where_clause = (
            f"(partner.company_id = {self.company_id.id} OR partner.company_id IS NULL)"
        )

        if self.report == "customers":
            where_clause += " AND partner.customer_rank > 0"

            if self.export_data == "all_export":
                where_clause += f"""
                AND (
                    partner.bmd_exported_customer = false
                    OR partner.bmd_exported_customer IS NULL
                    OR partner.bmd_reexport_customer = true
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
                    partner.bmd_exported_customer = false
                    OR partner.bmd_exported_customer IS NULL
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
