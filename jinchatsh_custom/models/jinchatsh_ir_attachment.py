# -*- coding: utf-8 -*-

from odoo import models, api

import logging

_logger = logging.getLogger(__name__)


class JinchatshIrAttachment(models.Model):
    _inherit = "ir.attachment"
    _description = "Jinchatsh Attachment"

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if order is None:
            order = 'create_date desc'
        return super().search_read(domain, fields=fields, offset=offset, limit=limit, order=order)
