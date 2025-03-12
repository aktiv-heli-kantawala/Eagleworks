/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";

export class L10nAtSelectRegisterPopup extends Component {
    static template = "ew_l10n_at_pos_cert.SelectRegisterPopup";
    static components = { Input, Dialog };
    static props = ["confirmKey?", "close", "getPayload?"];

    async setup() {
       /**
        Set up the initial state and get the available registers from POS
        Load the saved register from local storage and update if needed
        */
        super.setup();
        this.pos = usePos();
        this.state = useState({
            selectedRegisterId: false,
            availableRegisters: this.pos.l10n_at_register_ids,
            inherited_from_dialog: true,
        });
        var l10n_at_register = JSON.parse(localStorage['l10n_at_register'] || "{}")

        if (this.get_10nAtRegister() || !Object.keys(this.pos.l10n_at_register_ids).includes(l10n_at_register["id"])) {
            this.props.cancelKey = "Escape";
            await this.pos.setL10nAtRegister(l10n_at_register["id"])
        }
    }
    get_10nAtRegister(){
        /**
         Get the saved register data from local storage and convert it to an object
         If there's an error, return the stored value as a string instead
        */
        try {
                this.at_register=  browser.localStorage.getItem("l10n_at_registerdddd")  || "{}" ?  JSON.parse(browser.localStorage.getItem("l10n_at_registerdddd"))  || "{}": defaultValue;
         } catch {
                this.at_register =  browser.localStorage.getItem("l10n_at_registerdddd")  || "{}";
         }
//          browser.localStorage.removeItem('l10n_at_registerdddd');
        return this.at_register
    }
    async selectRegister(registerId) {
    /**
      Save the selected register and update it in POS
    If no null receipt is needed, open the opening control
    */
        this.state.selectedRegisterId = registerId;
        await this.pos.setL10nAtRegister(this.state.selectedRegisterId);
        this.confirm();
        if(!this.pos.isL10nAtNullReceiptNecessary()){
            this.pos.openOpeningControl();
        }
    }
    forceUnlock(selectedRegisterId) {
        /**
        Find the register with the given ID and mark it as not in use
        This allows the register to be used again if it was locked
        */
        this.state.availableRegisters.forEach(register => {
            if (register.id === selectedRegisterId) {
                register.is_in_use = false;
            }
        })
    }
    async confirm() {
        this.props.close({ confirmed: true, payload: await this.getPayload() });
    }
    async getPayload() {
        return null;
    }
}