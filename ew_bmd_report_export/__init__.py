from . import models
from . import wizards

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    partners = env["res.partner"].search(
        ["|", ("customer_rank", ">", 0), ("supplier_rank", ">", 0)], order="id asc"
    )
    for partner in partners:
        if partner.customer_rank and partner.customer_rank > 0:
            partner.write(
                {"debtor_number": env["ir.sequence"].next_by_code("res.partner.debtor")}
            )
        elif partner.supplier_rank and partner.supplier_rank > 0:
            partner.write(
                {
                    "creditor_number": env["ir.sequence"].next_by_code(
                        "res.partner.creditor"
                    )
                }
            )
    _logger.info("\nAssign debtor and creditor numbers for all customer/supplier")
