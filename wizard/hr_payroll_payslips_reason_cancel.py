# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class HrPayslipReasonCance(models.TransientModel):
    _name = 'hr.payslip.reason.cancel'
    _description = 'Motivo de Cancelación'

    @api.model
    def _default_cfdi_reason_cancel(self):
        ctx = self.env.context
        print('--------- ctx', ctx)
        return ctx.get('reason_cancel',False)    

    @api.model
    def _default_l10n_mx_edi_cfdi_uuid(self):
        ctx = self.env.context
        return ctx.get('uuid',False)    

    @api.model
    def _default_l10n_mx_edi_cfdi_uuid_to_cancel(self):
        ctx = self.env.context
        return ctx.get('to_cancel',False)    

    cfdi_reason_cancel = fields.Selection(
        selection=[
            ('01', u'[01] Comprobante Emitido con errores con relación'),
            ('02', u'[02] Comprobante Emitido con errores sin relación'),
            ('03', u'[03] No se llevo a cabo la operación'),
            ('04', u'[04] Operación nominativa relacionada en una factura global'),
        ],        
        string="CFDI Reason Cancel", copy=False, default=_default_cfdi_reason_cancel)
    l10n_mx_edi_cfdi_uuid = fields.Char(string='Folio Fiscal Relacionado', readonly=True,
        help='UUID del recibo que substituye este XML.', default=_default_l10n_mx_edi_cfdi_uuid)
    l10n_mx_edi_cfdi_uuid_to_cancel = fields.Char(string='Folio Fiscal a Cancelar', readonly=True,
        help='UUID del recibo que substituye este XML.', default=_default_l10n_mx_edi_cfdi_uuid_to_cancel)

    def button_cancel_xml(self):
        ctx = self.env.context
        rec_id = ctx.get('slip_id')
        if rec_id:
            record = self.env['hr.payslip'].browse(rec_id)
            print('------- self.cfdi_reason_cancel', self.cfdi_reason_cancel, ctx)
            return record.action_payslip_cancel_xml(reason_cancel=self.cfdi_reason_cancel)
        return {'type': 'ir.actions.act_window_close'}



