# EagleWorks Export BMD Reports

Custom wizard form allows exporting reports compatible with BMD software.

**Table of Contents**

* Features & Limitations
* Configuration
* Usage
* Development

---

## Features

* New Export Wizard: Enables exporting reports compatible with BMD software, with filters for dates, export data types (Un-Exported + Re-Export modified data or Only Un-Exported), and options to choose the company and report types.
* Report Types: Export various types of reports such as:
 Customer reports
 General Ledger report data
 Supplier reports
 Bank statement data
 Cash transactions data
 Journal Items data (both for in invoices and out invoices)
 All Export: Option to export all reports at once for BMD software.
* Assigned debitor(Customer) and creditor(vendor) number.

---

## Usage

* Users can export reports in CSV or XLSX format for:
 Bank statement data
 Cash transactions
 Journal Items data for in invoices
 Journal Items data for out invoices
 Additionally, users can choose to export all reports simultaneously.

---

## Development

* New Transient Model: Created 'bmd.reports'.
* New menu under accounting>reporting>BMD Reports>Export - BMD Reports 
* Fields Added: Fields for company, date from, date to, report type, report, and export data.
* Module Download: Module is downloadable and attachable for user convenience.
* Validation: Implemented validation to ensure there is data in the CSV or XLSX file before allowing download.

---