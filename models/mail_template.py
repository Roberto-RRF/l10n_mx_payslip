# -*- coding: utf-8 -*-

from odoo import models

class MailTemplate(models.Model):
    _inherit = "mail.template"

    def generate_email(self, res_ids, fields):
        res = super().generate_email(res_ids, fields)
        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False
        if self.model in ['hr.payslip']:
            for record in self.env[self.model].browse(res_ids):
                if record.company_id.country_id != self.env.ref('base.mx'):
                    continue
                attachment = record._get_l10n_mx_edi_signed_edi_document()
                if attachment:
                    (res[record.id] if multi_mode else res).setdefault('attachments', []).append((attachment.name, attachment.raw))
        return res
