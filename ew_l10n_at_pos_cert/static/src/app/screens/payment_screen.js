/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    //@override
    async _finalizeValidation() {
        /**
        If a null receipt was used, reset the flag before proceeding
        Try to finalize the order validation and handle errors if needed
        */
        if (this.pos.is_from_null_receipt){
              this.pos.is_from_null_receipt = false;
        }
        if (this.pos.getL10nAtRegister()) {
            try {
                await this.currentOrder.l10nAtSignTransaction();
                await super._finalizeValidation(...arguments)
            } catch (error) {
                throw error;
                // Below code block will never get called
                if (error.status === 0) {
                    this.trigger('l10n-at-no-internet-confirm-popup', super._finalizeValidation.bind(this));
                } else {
                    const message = { 'unknown': this.env._t('An unknown error has occurred!') };
                    this.trigger('l10n-at-error', { error, message });
                }
            }
        }
        else {
            await super._finalizeValidation(...arguments);
        }
    },
});
