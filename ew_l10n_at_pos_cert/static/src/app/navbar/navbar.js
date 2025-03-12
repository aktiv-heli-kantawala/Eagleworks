/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    openMenu() {
        /** Override the openMenu method to add a condition before opening the menu
             Prevent menu access if 'is_from_null_receipt' flag is set
            * This method is for we cannot perform any operations before validating the Null Receipt *
        */
        if (this.pos.is_from_null_receipt){
            this.pos._showIsFromNullReceiptError();
        }
        else{
            super.openMenu(...arguments);
        }
    }
})

