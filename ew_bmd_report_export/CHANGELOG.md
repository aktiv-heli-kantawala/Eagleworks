# EagleWorks Export BMD Reports

### Technical Name: ew_bmd_report_export

## Versions

### 18.0.1.0.0 (02/19/2025)
- Upgrade to Odoo 18
- Remove the menu item with `id='menu_export_bmd_reports'` as it is commented out.  
- Delete the `report_layout` file, along with the `report` and `css` folders, since they are not defined in the manifest file.  
- Modify the `code` field in the `account.account` model to be stored, as it is required in the report.  
- Remove the `base_document_layout` and  `base_document_layout_views` and `report_invoice` files, as they are also not defined in the manifest file.