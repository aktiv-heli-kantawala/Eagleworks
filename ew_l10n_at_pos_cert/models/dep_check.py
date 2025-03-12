import json
import logging
import os
import stat
import subprocess
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CheckDep(models.Model):
    _name = "ew_l10n_at_pos_cert.dep_check"
    _description = "Check DEP"

    # ----------------------------------------------------------
    # Fields
    # ----------------------------------------------------------

    name = fields.Char(
        string="Name", compute="_compute_name", store=True, readonly=True
    )

    register_id = fields.Many2one(
        comodel_name="ew_l10n_at_pos_cert.register",
        string="Register",
        required=True,
    )

    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Attachment",
        required=True,
        compute="_compute_attachment",
        store=True,
        readonly=False,
        domain='[("res_model", "=", "ew_l10n_at_pos_cert.register"), ("res_id", "=", register_id)]',
    )

    cryptographic_material_container = fields.Text(
        string="Cryptographic Material Container",
        compute="_compute_cryptographic_material_container",
    )

    work_dir = fields.Char(string="Work Dir", compute="_compute_work_dir", store=True)

    path_cmc = fields.Char(string="Path cmc", compute="_compute_path", readonly=True)

    path_dep = fields.Char(string="Path Dep", compute="_compute_path", readonly=True)

    path_run = fields.Char(string="Path Run", compute="_compute_path", readonly=True)

    path_output = fields.Char(
        string="Path Output", compute="_compute_path", readonly=True
    )

    run_script = fields.Text(string="Run Script", compute="_compute_run_script")

    output = fields.Text(string="Output", readonly=True)

    # ----------------------------------------------------------
    # Compute
    # ----------------------------------------------------------

    @api.depends("register_id")
    def _compute_attachment(self):
        """
        Compute the latest attachment related to the selected register.
        If a register is selected, assigns the most recent attachment;
        otherwise, sets the attachment to False.
        """
        for record in self:
            record.attachment_id = False
            if record.register_id:
                record.attachment_id = self.env["ir.attachment"].search(
                    [
                        ("res_model", "=", "ew_l10n_at_pos_cert.register"),
                        ("res_id", "=", record.register_id.id),
                    ],
                    order="create_date desc",
                    limit=1,
                )

    @api.depends("path_cmc", "path_dep", "path_output")
    def _compute_run_script(self):
        """
        Generates a Bash script for executing the DEP check with specified
        paths for cryptographic material, DEP file, and output directory.
        """
        exec_path = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("ew_l10n_at_pos_cert.regkassen_verification_exec_path", False)
        )
        for record in self:
            record.run_script = "\n".join(
                [
                    "#!/bin/bash",
                    "",
                    "java \\",
                    f"\t-jar {exec_path} \\",
                    "\t-v \\",
                    f"\t-c {record.path_cmc} \\",
                    f"\t-i {record.path_dep} \\",
                    f"\t-o {record.path_output}",
                    "",
                ]
            )

    @api.depends("work_dir")
    def _compute_path(self):
        """
        Computes file paths for cryptographic material, DEP file,
        execution script, and output based on the work directory.
        """
        for record in self:
            record.path_cmc = os.path.join(record.work_dir, "cmc.json")
            record.path_dep = os.path.join(record.work_dir, "dep.json")
            record.path_run = os.path.join(record.work_dir, "run.sh")
            record.path_output = os.path.join(record.work_dir, "output")

    @api.depends("attachment_id")
    def _compute_work_dir(self):
        """
        Computes the working directory path for the DEP check using the
        configuration parameter and the attachment's name, appending a unique suffix.
        """
        config_work_dir = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("ew_l10n_at_pos_cert.regkassen_verification_work_dir", False)
        )
        for record in self:
            path_dirs = []
            if config_work_dir:
                path_dirs.append(config_work_dir)
            if record.attachment_id:
                path_dirs.append(record.attachment_id.name)
            record.work_dir = (
                (os.path.join(*path_dirs) + "-" + uuid.uuid4().hex[-4:])
                if path_dirs
                else ""
            )

    @api.depends("register_id", "attachment_id")
    def _compute_name(self):
        """
        Computes the name of the record using the register's name and the
        attachment's name. Defaults to '/' if no values are available.
        """
        for record in self:
            name_values = []
            if record.register_id:
                name_values.append(record.register_id.name)
            if record.attachment_id:
                name_values.append(record.attachment_id.name)
            record.name = " - ".join(name_values) if name_values else "/"

    @api.depends("register_id")
    def _compute_cryptographic_material_container(self):
        """
        Computes a JSON structure containing cryptographic material details
        for the register, including AES keys and certificate information.
        """
        for record in self:
            cryptographic_material_container = {}
            if self.register_id:
                cryptographic_material_container = {
                    "base64AESKey": self.register_id.aes_key_b64,
                    "certificateOrPublicKeyMap": {
                        self.register_id.certificate_serial_number: {
                            "signatureDeviceType": "CERTIFICATE",
                            "id": self.register_id.certificate_serial_number,
                            "signatureCertificateOrPublicKey": self.register_id.certificate,
                        }
                    },
                }
            record.cryptographic_material_container = json.dumps(
                cryptographic_material_container, indent=4
            )

    # ----------------------------------------------------------
    # UI
    # ----------------------------------------------------------

    def action_wizard_check(self):
        """
        Executes the DEP check and returns an action to open the form view
        for the current record in a wizard interface.
        """
        self.ensure_one()
        self.action_check()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "ew_l10n_at_pos_cert.action_dep_check"
        )
        action.update(
            {
                "view_mode": "form",
                "views": [v for v in action["views"] if v[1] == "form"],
                "res_id": self.id,
            }
        )
        return action

    def action_check(self):
        """
        Initiates the DEP check process by invoking the `_check_dep` method
        for the selected records.
        """
        for record in self:
            record._check_dep()

    # ----------------------------------------------------------
    # Logic
    # ----------------------------------------------------------

    def _check_dep(self):
        """
        Handles the complete DEP check process by creating a working directory,
        generating required files, and executing the verification script.
        """
        for record in self:
            record._create_work_dir()
            record._create_work_files()
            record._run_check()

    def _run_check(self):
        """
        Runs the verification script in the working directory and captures
        the output for each record.
        """
        for record in self:
            process = subprocess.Popen(
                [record.path_run],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )
            record.output = process.stdout.read().decode()

    def _create_work_files(self):
        """
        Creates necessary files for the DEP check process, including the
        cryptographic material, DEP JSON, and execution script. Assigns proper permissions to the script.
        """
        for record in self:
            file_data = [
                (record.path_cmc, record.cryptographic_material_container),
                (
                    record.path_dep,
                    record.attachment_id.raw.decode() if record.attachment_id else "",
                ),
                (record.path_run, record.run_script),
            ]
            for file_path, content in file_data:
                if not os.path.exists(file_path):
                    with open(file_path, "w") as file:
                        file.write(content)
            os.chmod(record.path_run, stat.S_IRWXU)

    def _create_work_dir(self):
        """
        Creates the working directory for DEP check files. Raises an error
        if the configuration parameter for the directory is not defined.
        """
        if (
            not self.env["ir.config_parameter"]
            .sudo()
            .get_param("ew_l10n_at_pos_cert.regkassen_verification_work_dir")
        ):
            raise UserError(
                _("Please define a work directory in the settings for DEP checks.")
            )
        for record in self:
            try:
                os.mkdir(record.work_dir)
            except Exception as e:
                _logger.error(e)
                raise ValidationError(str(e))
