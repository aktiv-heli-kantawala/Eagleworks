/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { L10nAtPrintNullReceiptPopup } from "@ew_l10n_at_pos_cert/app/popups/PrintNullReceiptPopup";
import { L10nAtSelectRegisterPopup } from "@ew_l10n_at_pos_cert/app/popups/SelectRegisterPopup";
import { TaxError, NullReceiptProductError } from "@ew_l10n_at_pos_cert/app/error";
import { rpc } from "@web/core/network/rpc";
import { browser } from "@web/core/browser/browser";
import { makeAwaitable, ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { registry } from "@web/core/registry";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        /**
        Define VAT rate mappings for different tax categories
        */
        this.vatRateMapping = {
            20: 'NORMAL',
            10: 'REDUCED_1',
            13: 'REDUCED_2',
            19: 'SPECIAL',
            0: 'NULL'
        }
    },
    async processServerData() {
    /**
     Override the method to process additional server data related to certification registers
    Ensures that certification register details are properly loaded for further operations
    */
        await super.processServerData();
        if (this.models["ew_l10n_at_pos_cert.register"]){
            this.cert_register = this.models["ew_l10n_at_pos_cert.register"].getAll();
            if (this.cert_register) {
                this.l10n_at_register_ids = this.cert_register;
            }
        }
    },
    isCountryAustria() {
    /**
             Store whether the company is based in Austria in local storage
    Returns the boolean value indicating if the company is in Austria
    */
        browser.localStorage.setItem('isCountryAustria', JSON.stringify(this.config.is_company_country_austria));
        return this.config.is_company_country_austria;
    },
    getL10nAtRegister() {
    /**
    Save the current local register information into local storage
    Returns the stored register data for further use
    */
        browser.localStorage.setItem('l10n_at_registeraaa', JSON.stringify(this.l10n_at_register));
        browser.localStorage.setItem('l10n_at_registerdddd', JSON.stringify(this.l10n_at_register));
        return this.l10n_at_register;
    },
    async selectPartner(isEditMode = false, missingFields = []) {
     /**
         Checks if the transaction is from a null receipt and displays an error if true
        Otherwise, proceeds with the default partner selection process
     */
        if (this.is_from_null_receipt){
            this._showIsFromNullReceiptError();
        }
        else{
            super.selectPartner(...arguments);
        }
    },
    isL10nAtNullReceiptNecessary() {
        /**
              Determines whether a null receipt is necessary based on the last recorded null receipt date.
            If no register is set or the last null receipt was in a previous month, returns true.
        */
        if (!this.getL10nAtRegister()) {
            return false;
        }
        if (!this.getL10nAtRegister().last_null_receipt_date) {
            return true;
        } else if ((new Date(this.getL10nAtRegister().last_null_receipt_date)).getMonth() != (new Date()).getMonth()) {
            return true;
        }
        return false
    },
    async setL10nAtRegister(id) {
    /**
        Sets the L10n AT register based on the provided ID.
        Fetches register details from the server and stores them locally.
    */
        try {
            if (id) {
                if(typeof id === 'number'){
                    var id = id;
                }
                if (typeof id === 'object'){
                    id = id.id;
                }
                let l10nAtRegister = await rpc(`${this.session._base_url}/register/${id}`, { lock: true }, {})
                this.l10n_at_register = l10nAtRegister;
                 localStorage['l10n_at_register'] = JSON.stringify({
                    id: l10nAtRegister.id,
                    session_token: l10nAtRegister.session_token
                });
            }
            else {
                this.l10n_at_register = null;
            }
        } catch (e) {
            this.l10n_at_register = null;
            throw e;
        }
    },
    async clearL10nAtRegister() {
    /**
        Clears the currently set L10n AT register.
        Unlocks the register on the server before resetting it locally.
    */
        try {
            await rpc(`${this.session._base_url}/register/${this.l10n_at_register.id}`, { lock: false, session_token: this.l10n_at_register.session_token }, {})
            this.l10n_at_register = null;
        } catch (e) {
            this.l10n_at_register = null;
            throw e;
        }
    },
    async openL10nAtSelectRegister() {
    /**
             Opens a dialog to select an L10n AT register if one is not already set.
            Also handles the process for printing a null receipt if necessary.
    */
        if (
            this.config.l10n_at_register_ids
            && this.config.l10n_at_register_ids.length
            && !this.getL10nAtRegister()
        ) {
            if (this.config.l10n_at_register_ids.length == 1) {
                await this.setL10nAtRegister(this.config.l10n_at_register_ids[0]);
            } else {
                await makeAwaitable(this.dialog, L10nAtSelectRegisterPopup);
            }
        }
        if (this.isL10nAtNullReceiptNecessary()) {
            let  nullreceipt  = await this.dialog.add(L10nAtPrintNullReceiptPopup, {});
            this.getL10nAtRegister().last_null_receipt_date = new Date().toISOString().split('T')[0];
            if (nullreceipt) {
                this.is_from_null_receipt = true;
                this.session.state = 'opened';
                const props = {};
                const { name: screenName } = this.get_order().get_screen_data();
                if (screenName === "PaymentScreen") {
                    props.orderUuid = this.selectedOrderUuid;
                }
                this.showScreen('PaymentScreen', props);
            }
        }
    },
    async _showTaxError() {
    /**
        This method displays an error message when a product has an invalid tax amount.
        It ensures that only predefined VAT rates are allowed for products.
    */
        const rates = Object.keys(this.vatRateMapping);
        const title = _t("Tax error");
        let body;
        const ratesText = [rates.slice(0, -1).join(', '), rates.slice(-1)[0]].join(' and ');
        body = _t('Product has an invalid tax amount. Only the following rates are allowed: %s.', ratesText);
        await this.dialog.add(AlertDialog, { title, body });
    },
    async _showNullReceiptProductError() {
        /**
             This method displays an error message when a null receipt product
            is used together with other products in a single order.
        */
        const title = _t('Null receipt error');
        const body = _t('Null receipt product can not be used with other products in one order!');
        await this.dialog.add(AlertDialog, { title, body });
    },
    async _showIsFromNullReceiptError() {
    /**
        This method displays an error message when a user attempts to perform
        an operation before validating the Null Receipt.

    */
        const title = _t('Validation error');
        const body = _t('You cannot perform any operations before validating the Null Receipt!');
        await this.dialog.add(AlertDialog, { title, body });
    },
    async addLineToCurrentOrder(vals, opt = {}, configure = true) {
        /**
             This method attempts to add a line item to the current order.
            If an error occurs, it handles tax and null receipt product errors accordingly.
        */
        var res = false;
        try {
            return super.addLineToCurrentOrder(vals, opt, configure);
        } catch (error) {
            if (this.getL10nAtRegister() && error instanceof TaxError) {
                await this._showTaxError();
            } else if (error instanceof NullReceiptProductError) {
                await this._showNullReceiptProductError();
            } else {
                throw error;
            }
        }
        return res
    },
    async addLineToOrder(vals, order, opts = {}, configure = true) {
    /*
        It first checks if the point of sale (pos) has a localization setting at the register.
        If it does, it retrieves a null product from the database based on a specific ID.
        It then checks if the product being added is not the null product and either has no taxes or
        the taxes are not included in the VAT rate mapping. If the conditions are not met, it throws a `TaxError`.
        */
        if (this.getL10nAtRegister()) {
            const nullProduct = this.config.l10n_at_null_receipt_product_id;
            if (vals.product_id.id != nullProduct.id && (vals.product_id.taxes_id.length === 0 || vals.product_id.taxes_id.filter(
                (tax) => {
                    return !Object.keys(this.vatRateMapping).includes(
                        String(tax.amount)
                    )
                }).length)) {
                const rates = Object.keys(this.vatRateMapping);
                const ratesText = [rates.slice(0, -1).join(', '), rates.slice(-1)[0]].join(' and ');
                throw new TaxError(vals.product_id,ratesText);
            }
        }

        if (this.get_order().get_orderlines().length && this.config.l10n_at_null_receipt_product_id && (
            this.get_order().get_orderlines()[0].product_id.id === this.config.l10n_at_null_receipt_product_id.id ||
            vals.product_id.id === this.config.l10n_at_null_receipt_product_id.id
        )) {
            throw new NullReceiptProductError();
        }
        super.addLineToOrder(vals,order,opts,configure);
    },
    showScreen(name, props) {
        /**
        This method controls screen transitions while ensuring validation for null receipts.
        If a null receipt is active, it prevents navigation to the ProductScreen.
        */
        if (this.is_from_null_receipt && name === 'ProductScreen') {
               this._showIsFromNullReceiptError();
            }
              else {
                return super.showScreen(...arguments);
            }
   },
});
