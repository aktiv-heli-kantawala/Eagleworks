/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted} from "@odoo/owl";

patch(ProductScreen.prototype, {
    setup() {
    /**
      Run setup and call a function when the component is mounted
     Opens the register selection screen automatically
    */
        super.setup();
        onMounted(() => {
                this.pos.openL10nAtSelectRegister();
        });
    },
    //@Override
    async _barcodeProductAction(code) {
        /**
         Process the scanned product barcode and handle possible errors
         Show specific error messages for tax issues or null receipt products
        */
        try {
            await super._barcodeProductAction(...arguments);
        } catch (error) {
            if (this.pos.getL10nAtRegister() && error instanceof TaxError) {
                await this.pos._showTaxError();
            } else if (error instanceof NullReceiptProductError) {
                await this.pos._showNullReceiptProductError();
            } else {
                throw error;
            }
        }
    }
});
