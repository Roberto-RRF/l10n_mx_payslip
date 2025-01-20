# -*- coding: utf-8 -*-

from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    cfdi_registropatronal_id = fields.Many2one('l10n_mx_payroll.regpat', string='Registro patronal')

    def get_edi_cfdi_version(self):
        cfdi_edi_format = self.env.ref('l10n_mx_edi.edi_cfdi_3_3')
        version = cfdi_edi_format.name.find("4.0")
        return "4.0" if version >= 0 else "3.3"    

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cfdi_registropatronal_id = fields.Many2one('l10n_mx_payroll.regpat', related='company_id.cfdi_registropatronal_id', readonly=False)
