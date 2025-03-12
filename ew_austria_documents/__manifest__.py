{
    "name": "EagleWorks Custom Document",
    "version": "18.0.1.0.0",
    "description": "EagleWorks Custom Document",
    "author": "Aktiv Software",
    "category": "Accounting/Accounting",
    "website": "https://www.aktivsoftware.com",
    "depends": ["l10n_din5008", "account_accountant", "sale"],
    "data": [
        "report/eagleworks_report.xml",
        "data/report_layout.xml",
        "views/base_document_layout_views.xml",
        "report/report_invoice.xml",
        "report/account_report.xml",
        "report/report_template.xml",
        "views/account_move_view.xml",
        "views/res_company_views.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "ew_austria_documents/static/src/scss/report_ew_layout.scss",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
