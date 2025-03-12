/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {
    async confirm() {
        /**
            Override the confirm method to handle localization clearing before confirmation
            Ensures errors during the process are caught and logged
            * when close session it will make register null *
        */
        try {
            await this.pos.clearL10nAtRegister();
        } catch (e) {
            console.log(e);
        }
        super.confirm();
    },
});
