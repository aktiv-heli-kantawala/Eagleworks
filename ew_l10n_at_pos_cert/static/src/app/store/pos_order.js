/** @odoo-module */
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { TaxError, NullReceiptProductError } from "@ew_l10n_at_pos_cert/app/error";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { browser } from "@web/core/browser/browser";
import { roundDecimals as round_di } from "@web/core/utils/numbers";

const { DateTime } = luxon;

patch(PosOrder.prototype, {
    setup() {
    /**
     Set up VAT rate mappings and check if the country is Austria
    Load register details if available and initialize related properties
    */
        super.setup(...arguments);
        this.vatRateMapping = {
            20: 'NORMAL',
            10: 'REDUCED_1',
            13: 'REDUCED_2',
            19: 'SPECIAL',
            0: 'NULL'
        }
          var austriaaa = browser.localStorage.getItem("isCountryAustria") || "{}"
         try {
                this.is_CountryAustria =  austriaaa ?  JSON.parse(austriaaa) : defaultValue;
         } catch {
                this.is_CountryAustria =  austriaaa;
         }
        if (this.get_L10nAtRegister().hasOwnProperty()) {
            this.l10n_at_number = this.get_L10nAtRegister().turnover;
            this.l10n_at_register_id = this.models['ew_l10n_at_pos_cert.register'].get(this.get_L10nAtRegister().id) || null;
            this.l10n_at_turnover = this.l10n_at_turnover || 0;
            this.l10n_at_type = this.l10n_at_type || null;
            this.l10n_at_jws_signature = this.l10n_at_jws_signature || null;
            this.l10n_at_mrc_signature = this.l10n_at_mrc_signature || null;
            this.l10n_at_certificate = this.l10n_at_certificate || null;
            this.l10n_at_certificate_issuer =  null;
            this.l10n_at_sd_not_available = this.l10n_at_sd_not_available || null;
        }
    },
    get_L10nAtRegister(){
    /**
    Get the stored register data from local storage and convert it to an object
    If there's an error, return the stored value as a string instead
    */
        try {
                this.l10n_at_registeraaa =  browser.localStorage.getItem("l10n_at_registeraaa")  || "{}" ?  JSON.parse(browser.localStorage.getItem("l10n_at_registeraaa"))  || "{}": defaultValue;
         } catch {
                this.l10n_at_registeraaa =  browser.localStorage.getItem("l10n_at_registeraaa")  || "{}";
         }
//         browser.localStorage.removeItem('l10n_at_registeraaa');
        return this.l10n_at_registeraaa
    },
    recomputeOrderData() {
    /**
     Update order details and get the current register data
    Fetch the register information using its ID
    */
        super.recomputeOrderData(...arguments);
        var register = this.get_L10nAtRegister()
        if (this.models['ew_l10n_at_pos_cert.register']){
            this.l10n_at_register_id = this.models['ew_l10n_at_pos_cert.register'].get(register.id)
        }
    },
    export_for_printing() {
    /**
    Generate receipt data and include Austria-specific tax details if available
    If a signature exists, add a QR code and register details to the receipt
    */
        const receipt = super.export_for_printing(...arguments);
        if (this.get_L10nAtRegister()) {
            if (this.l10n_at_mrc_signature) {
                receipt['l10n_at_mrc_signature'] = this.l10n_at_mrc_signature;
                const l10n_at_mrc_qr = QRCode.generatePNG(this.l10n_at_mrc_signature, {
                    ecclevel: "M",
                    format: "html",
                    fillcolor: "#ffffff",
                    textcolor: "#000000",
                    margin: 4,
                    modulesize: 4,
                });
                receipt['l10n_at_mrc_qr'] = l10n_at_mrc_qr;
                const parts = this.l10n_at_mrc_signature.split('_');
                if (parts.length > 3) {
                    receipt['l10n_at_register_name'] = parts[2];
                    receipt['l10n_at_number'] = parts[3];
                }
            } else {
                receipt['l10n_at_issue'] = true;
            }
        } else if (this.isCountryAustriaaa && !this.get_L10nAtRegister()) {
            receipt['test_environment'] = true;
        }

        return receipt;
    },
    _createAmountPerVatRateArray() {
    /**
     Organize tax amounts by VAT rate categories
    Sum up the total amount for each VAT category based on tax IDs
    */
        const rateIds = {
            'NORMAL': [],
            'REDUCED_1': [],
            'REDUCED_2': [],
            'SPECIAL': [],
            'NULL': [],
        };
        this.get_tax_details().forEach((detail) => {
            rateIds[this.vatRateMapping[detail.tax.amount]].push(detail.tax.id);
        });
        const amountPerVatRate = { 'NORMAL': 0, 'REDUCED_1': 0, 'REDUCED_2': 0, 'NULL': 0, 'SPECIAL': 0 };
        for (var rate in rateIds) {
            rateIds[rate].forEach((id) => {
                amountPerVatRate[rate] += this.get_total_for_taxes(id);
            });
        }
        return amountPerVatRate;
    },
    l10nAtFormatRoundDecimalsCurrency(value) {
    /**
        Round the given value to the currency's decimal places
        Convert the decimal separator from '.' to ',' for localization
    */
        const decimals = this.currency.decimal_places;
        const new_value = round_di(value, decimals).toFixed(decimals);
        return new_value.toString().replace('.', ',')
    },
    async l10nAtSignTransaction() {
    /**
        Generate and sign the receipt data using encryption
        Handles different receipt types and updates transaction details
    */
        if (!this.l10n_at_signature) {
            const self = this;
            const rates = this._createAmountPerVatRateArray();
            let receipt_number = this.get_L10nAtRegister().receipt_counter + 1

            this.l10n_at_sd_not_available = false;
            this.l10n_at_type = 'STANDARD_RECEIPT'
            const null_receipt_id = this.config.l10n_at_null_receipt_product_id.id;
            if (!this.get_total_with_tax() && this.get_orderlines()[0].product_id.id === null_receipt_id) {
                this.l10n_at_type = 'NULL_RECEIPT'
                if (!this.get_L10nAtRegister().last_receipt_hash) {
                    this.l10n_at_type = 'START_RECEIPT'
                }
            }

            let turnover = this.get_L10nAtRegister().turnover;
            let turnover_enc;
            if (this.l10n_at_type === 'TRAINING_RECEIPT') {
                turnover_enc = 'VFJB'
            } else {
                turnover = turnover + Math.round(this.get_total_with_tax() * 100)
                if (this.l10n_at_type === 'REVERSAL_RECEIPT') {
                    turnover_enc = 'U1RP'
                } else {
                    let enc_turnover = new DataView(new ArrayBuffer(8));
                    enc_turnover.setBigInt64(0, BigInt(turnover), false)
                    const iv_data = this.get_L10nAtRegister().name + receipt_number.toString();
                    const iv_sha256 = CryptoJS.SHA256(iv_data)
                    const iv_hash = CryptoJS.lib.WordArray.create(
                        iv_sha256.words.slice(0, (8 * 16) / iv_sha256.sigBytes)
                    );
                    const key = CryptoJS.enc.Base64.parse(this.get_L10nAtRegister().aes_key_b64)
                    const wa_turnover = CryptoJS.lib.WordArray.create(enc_turnover.buffer)
                    const turnover_aes = CryptoJS.AES.encrypt(wa_turnover, key, {
                        iv: iv_hash,
                        mode: CryptoJS.mode.CTR,
                        padding: CryptoJS.pad.NoPadding,
                    })
                    turnover_enc = turnover_aes.toString()
                }
            }

            let last_receipt_hash = this.get_L10nAtRegister().last_receipt_hash
            if (!last_receipt_hash) {
                const last_receipt_sha256 = CryptoJS.SHA256(
                    this.get_L10nAtRegister().name
                )
                last_receipt_hash = CryptoJS.lib.WordArray.create(last_receipt_sha256.words.slice(
                    0,
                    (8 * 8) / last_receipt_sha256.sigBytes
                )).toString(CryptoJS.enc.Base64)
            }
            const data_to_sign = [
                '',
                'R1-' + this.get_L10nAtRegister().zda_identity,
                this.get_L10nAtRegister().name,
                receipt_number.toString(),
                DateTime.now().toFormat('yyyy-MM-dd\'T\'HH:mm:ss'),

                this.l10nAtFormatRoundDecimalsCurrency(rates['NORMAL']),
                this.l10nAtFormatRoundDecimalsCurrency(rates['REDUCED_1']),
                this.l10nAtFormatRoundDecimalsCurrency(rates['REDUCED_2']),
                this.l10nAtFormatRoundDecimalsCurrency(rates['NULL']),
                this.l10nAtFormatRoundDecimalsCurrency(rates['SPECIAL']),
                turnover_enc,
                this.get_L10nAtRegister().certificate_serial_number,
                last_receipt_hash,
            ].join('_')

            return await rpc(
                `${this.session._base_url}/register/sign/${this.get_L10nAtRegister().id}`,
                { sign_data: data_to_sign }, {}
            ).then((data) => {
                self.l10nAtSetGeneralOrderFields(
                    self,
                    receipt_number,
                    turnover,
                    data['jws_signature'],
                    data['mrc_signature'],
                    false
                );
            }).catch(async (error) => {
                if (!error.status || error.status && error.status === 404 && self.l10n_at_type !== 'NULL_RECEIPT') {
                    const jws_signature = [
                        'eyJhbGciOiJFUzI1NiJ9',  // Note: encoded '{"alg":"ES256"}'
                        btoa(data_to_sign),
                        'U2ljaGVyaGVpdHNlaW5yaWNodHVuZyBhdXNnZWZhbGxlbg',  // Note: encoded 'Sicherheitseinrichtung ausgefallen'
                    ].join('.')
                    const mrc_signature = [
                        data_to_sign,
                        'U2ljaGVyaGVpdHNlaW5yaWNodHVuZyBhdXNnZWZhbGxlbg',  // Note: encoded 'Sicherheitseinrichtung ausgefallen'
                    ].join('_');
                    self.l10nAtSetGeneralOrderFields(
                        self,
                        receipt_number,
                        turnover,
                        jws_signature,
                        mrc_signature,
                        true
                    );
                } else {
                    return Promise.reject(error);
                }
            });
        }
    },
    l10nAtSetGeneralOrderFields(self, receipt_number, turnover, jws_signature, mrc_signature, sd_not_available) {
        this.l10n_at_number = receipt_number;
        this.l10n_at_turnover = turnover;
        this.l10n_at_register_id = this.get_L10nAtRegister().id;
        this.l10n_at_certificate = this.get_L10nAtRegister().certificate;
        this.l10n_at_certificate_issuer = this.get_L10nAtRegister().certificate_issuer;
        this.l10n_at_jws_signature = jws_signature
        this.l10n_at_mrc_signature = mrc_signature
        this.l10n_at_sd_not_available = sd_not_available;
        this.get_L10nAtRegister().turnover = turnover;
        this.get_L10nAtRegister().receipt_counter = receipt_number;
        this.get_L10nAtRegister().outage = sd_not_available;
        const last_receipt_sha256 = CryptoJS.SHA256(self.l10n_at_jws_signature);
        this.get_L10nAtRegister().last_receipt_hash = CryptoJS.lib.WordArray.create(
            last_receipt_sha256.words.slice(
                0,
                (8 * 8) / last_receipt_sha256.sigBytes
            )
        ).toString(CryptoJS.enc.Base64);
    }
});
