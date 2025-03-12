/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";

class CustomDialog extends Dialog {
    onEscape() {}
}

export class L10nAtPrintNullReceiptPopup extends Component {
    static template = "ew_l10n_at_pos_cert.PrintNullReceiptPopup";
    static defaultProps = { cancelKey: false };
    static components = { Dialog: CustomDialog };
    static props = {
        close: Function,
    };
    setup() {
        /**
           Set up the initial state and decide the type of receipt based on the last null receipt date
           Change the receipt type depending on how much time has passed since the last null receipt
        */
        super.setup();
        this.pos = usePos();
        this.state = useState({
            lastNullReceiptDate: false,
            receiptType: 'NULL'
        });
        if (!this.pos.getL10nAtRegister().last_null_receipt_date) {
            this.state.receiptType = 'START';
        } else {
            this.state.lastNullReceiptDate = new Date(
                this.pos.getL10nAtRegister().last_null_receipt_date
            )
            let currentMonth = (new Date()).getMonth();
            let lastNullReceiptMonth = this.state.lastNullReceiptDate.getMonth();
            lastNullReceiptMonth = 2;
            if (currentMonth === 0) {
                currentMonth = 12;
            }
            if (currentMonth > lastNullReceiptMonth) {
                this.state.receiptType = 'MONTH'
                if (currentMonth === 12) {
                    this.state.receiptType = 'YEAR'
                }
            }
        }
    }
    async confirm() {
        /**
            The function creates a new order in a POS system and adds a null product with specific details
            to the order.
        */
        const order = this.pos.add_new_order();
        const nullProduct = this.pos.config.l10n_at_null_receipt_product_id;
        const line = await this.pos.addLineToCurrentOrder({
                product_id: nullProduct,
                price_unit: 0,
                qty: 1,
         });
          this.props.close();
    }
}
