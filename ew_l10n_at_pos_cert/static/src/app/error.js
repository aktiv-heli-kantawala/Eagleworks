/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class TaxError extends Error {
    constructor(product,ratesText) {
        super(`Product has an invalid tax amount. Only the following rates are allowed: ${ratesText}.`)
    }
}

function taxErrorHandler(env, _error, originalError) {
    if (originalError instanceof TaxError) {
        env.services.dialog.add(AlertDialog, {
            title: _t("Tax Error"),
            body: originalError.message,
        });
        return true;
    }
}

registry.category("error_handlers").add("taxErrorHandler", taxErrorHandler);

export class NullReceiptProductError extends Error {
    constructor() {
        super('Null receipt product can not be used with other products in one order!')
    }
}

function nullreceiptHandler(env, _error, originalError) {
    if (originalError instanceof NullReceiptProductError) {
        env.services.dialog.add(AlertDialog, {
            title: _t("Null receipt error"),
            body: originalError.message,
        });
        return true;
    }
}

registry.category("error_handlers").add("nullreceiptHandler", nullreceiptHandler);

