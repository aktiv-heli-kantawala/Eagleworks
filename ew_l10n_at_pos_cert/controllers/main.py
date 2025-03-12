from odoo import http


class MainController(http.Controller):
    @http.route("/register/<int:id>", type="json", auth="user", cors="*")
    def register_lock_unlock(self, id, lock, session_token=False):
        """
        Handle locking/unlocking of a register based on given conditions.

        :param id: ID of the register to be locked/unlocked.
        :param lock: Boolean flag indicating whether to lock (True) or unlock (False) the register.
        :param session_token: Optional session token required for unlocking, default is False.

        :return: Result of lock/unlock operation or False if the register is not found.
        """
        register = http.request.env["ew_l10n_at_pos_cert.register"].search(
            [("id", "=", id)]
        )
        if register:
            return (
                register.lock_register()
                if lock
                else register.unlock_register(session_token)
            )
        return False

    @http.route("/register/sign/<int:id>", type="json", auth="user", cors="*")
    def register_sign(self, id, sign_data=""):
        """
        Sign a specific register using the provided sign data.

        :param id: ID of the register to be signed.
        :param sign_data: Additional data used for the signing operation (default is an empty string).

        :return: Result of the `sign` method on the register object.
        """
        return (
            http.request.env["ew_l10n_at_pos_cert.register"]
            .search([("id", "=", id)])
            .sign(sign_data)
        )
