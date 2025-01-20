# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import logging
import re
import base64
from collections import defaultdict
from lxml import etree, objectify
from lxml.objectify import fromstring
from dateutil.relativedelta import relativedelta
from datetime import datetime
from pytz import timezone
from datetime import date, datetime, time
import unicodedata
import codecs

from werkzeug.urls import url_quote, url_quote_plus
import odoo
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
#from odoo.addons.hr_payroll.models.browsable_object import BrowsableObject
from odoo.tools.misc import format_date
from odoo.addons.base.models.ir_qweb import keep_query


from PyPDF2 import PdfFileWriter, PdfFileReader 

_logger = logging.getLogger(__name__)

CFDI_XSLT_CADENA = 'l10n_mx_edi/data/3.3/cadenaoriginal.xslt'
CFDI_XSLT_CADENA_TFD = 'l10n_mx_edi/data/xslt/3.3/cadenaoriginal_TFD_1_1.xslt'
ATTACHMENT_NAME = 'CFDI_Payslip_{}.xml'

def remove_accents(s):
    def remove_accent1(c):
        return unicodedata.normalize('NFD', c)[0]
    return u''.join(map(remove_accent1, s))

class DefaultDictPayroll(defaultdict):
    def get(self, key, default=None):
        if key not in self and default is not None:
            self[key] = default
        return self[key]

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def write(self, vals):
        ctx = self._context
        AttachmentModel = self.env['ir.attachment']
        if vals.get('res_model') == 'hr.payslip':
            for rec in self:
                res_model = vals.get('res_model', '')
                res_id = vals.get('res_id', 0)
                attach_id = AttachmentModel.search([('name', '=', rec.name), ('res_model', '=', res_model), ('res_id', '=', res_id), ('id', '!=', rec.id)])
                if attach_id:
                    continue
                else:
                    res = super(IrAttachment, rec).write(vals)
        else:
            return super(IrAttachment, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        ctx = self._context
        for vals in vals_list:
            if ctx.get('encript_pdf', False) == True and vals.get('name', '').endswith('.pdf'):
                empl_code = ctx.get('cfdi_code_emp')
                pdf_content = base64.decodebytes(vals.get('datas'))
                buffer = io.BytesIO(pdf_content)
                out = PdfFileWriter()
                file = PdfFileReader(buffer)
                num = file.numPages
                for idx in range(num): 
                    page = file.getPage(idx) 
                    out.addPage(page)
                out.encrypt(empl_code)
                out.write( buffer )
                datas = buffer.getvalue()
                vals.update({
                    'datas': base64.encodebytes( datas )
                })
        res = super(IrAttachment, self).create(vals_list)
        return res

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _postprocess_pdf_report(self, record, buffer):
        if record._name == 'hr.payslip':
            empl_code = record.employee_id.cfdi_code_emp or record.employee_id.identification_id or ''
            if empl_code:
                out = PdfFileWriter()
                file = PdfFileReader(buffer)
                num = file.numPages
                for idx in range(num): 
                    page = file.getPage(idx) 
                    out.addPage(page)
                out.encrypt(empl_code)
                out.write( buffer )
        return super()._postprocess_pdf_report(record, buffer)

class HrPayslipUuidHistory(models.Model):
    _name = 'l10n_mx_payroll.uuid.history'
    _description = 'HrPayslipUuidHistory'

    @api.model
    def _default_cfdi_reason_cancel(self):
        ctx = self._context
        return ctx.get('reason_cancel',False)    

    name = fields.Char(related='slip_id.number', string='Recibo', store=True)
    employee_id = fields.Many2one(related='slip_id.employee_id', string="Empleado", store=True)
    cfdi_reason_cancel = fields.Selection(
        selection=[
            ('01', u'[01] Comprobante Emitido con errores con relación'),
            ('02', u'[02] Comprobante Emitido con errores sin relación'),
            ('03', u'[03] No se llevo a cabo la operación'),
            ('04', u'[04] Operación nominativa relacionada en una factura global'),
        ],        
        string="CFDI Reason Cancel", copy=False, default=_default_cfdi_reason_cancel)
    l10n_mx_edi_version = fields.Char(string="CFDI version", copy=False, readonly=True, store=True)    
    l10n_mx_edi_sat_status = fields.Selection(
        selection=[
            ('none', "State not defined"),
            ('undefined', "Not Synced Yet"),
            ('not_found', "Not Found"),
            ('cancelled', "Cancelled"),
            ('valid', "Valid"),
        ],
        string="SAT status", readonly=True, copy=False, required=True,
        default='undefined',
        help="Refers to the status of the journal entry inside the SAT system.")    
    l10n_mx_edi_post_time = fields.Datetime(
        string="Posted Time", readonly=True, copy=False,
        help="Keep empty to use the current México central time")
    l10n_mx_edi_cfdi_uuid = fields.Char(string='Fiscal Folio.', copy=False, readonly=True,
        help='Folio in electronic invoice, is returned by SAT when send to stamp.')
    l10n_mx_edi_cfdi_customer_rfc = fields.Char(string='Customer RFC', copy=False, readonly=True,
        help='The customer tax identification number.')
    l10n_mx_edi_status = fields.Selection(
        selection=[
            ('to_send', 'To Send'),
            ('sent', 'Sent'),
            ('to_cancel', 'To Cancel'),
            ('cancelled', 'Cancelled')
        ],
        string='MX EDI status',
        copy=False)
    invoice_date = fields.Date(string='Invoice CFDI', readonly=True, index=True, copy=False)
    l10n_mx_edi_cfdi_supplier_rfc = fields.Char(string='Supplier RFC', copy=False, readonly=True,
        help='The supplier tax identification number.')
    l10n_mx_edi_cfdi_amount = fields.Monetary(string='Total Amount', copy=False, readonly=True,
        help='The total amount reported on the cfdi.')
    currency_id = fields.Many2one(related='slip_id.currency_id')
    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade')
    state = fields.Selection(
        selection=[('to_cancel', 'Para Cancelar'), ('cancelled', 'Cancelled')], string='Estado', copy=False, default='to_cancel')


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model
    def _default_cfdi_date_payment(self):
        ctx = self._context
        cfdi_date_payment = fields.Date.to_string(date.today().replace(day=1))
        if 'active_model' in ctx:
            run_id = self.env[ctx['active_model']].browse(ctx['active_id'])
            cfdi_date_payment = run_id.cfdi_date_payment
        return cfdi_date_payment  

    cfdi_date_payment = fields.Date(string="Fecha pago", required=True, default=_default_cfdi_date_payment)
    l10n_mx_edi_sendemail = fields.Boolean(string="Send Email", default=False)
    l10n_mx_edi_xmlcfdi = fields.Boolean(string="Post XML CFDI", default=False)

    # ==== CFDI flow fields ====
    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_mx_edi_content = fields.Binary() # compute='_l10n_mx_edi_compute_edi_content', compute_sudo=True
    l10n_mx_edi_error = fields.Char(copy=False)
    l10n_mx_edi_status = fields.Selection(
        selection=[
            ('to_send', 'To Send'),
            ('sent', 'Sent'),
            ('to_cancel', 'To Cancel'),
            ('cancelled', 'Cancelled')
        ],
        string='MX EDI status',
        copy=False)
    l10n_mx_edi_sat_status = fields.Selection(
        selection=[
            ('valid', 'Valid'),
            ('cancelled', 'Cancelled'),
            ('not_found', 'Not Found'),
            ('none', 'State not defined'),
        ],
        string='SAT Status',
        copy=False)
    # l10n_mx_edi_cfdi_uuid = fields.Char('Fiscal Folio', copy=False)
    l10n_mx_edi_origin = fields.Char(
        string='CFDI Origin',
        copy=False,
        help="Specify the existing Fiscal Folios to replace. Prepend with '04|'")
    l10n_mx_edi_cancel_invoice_id = fields.Many2one(
        comodel_name='hr.payslip',
        string="Substituted By",
        compute='_compute_l10n_mx_edi_cancel',
        readonly=True)
    l10n_mx_edi_cfdi_file_id = fields.Many2one('ir.attachment', string='CFDI file', copy=False)

    # ==== CFDI flow fields ====
    l10n_mx_edi_force_generate_cfdi = fields.Boolean(string='Generate CFDI')
    invoice_date = fields.Date(string='Invoice CFDI', readonly=True, index=True, copy=False)
    l10n_mx_edi_post_time = fields.Datetime(
        string="Posted Time", readonly=True, copy=False,
        help="Keep empty to use the current México central time")


    # ==== CFDI certificate fields ====
    l10n_mx_edi_certificate_id = fields.Many2one(
        comodel_name='l10n_mx_edi.certificate',
        string="Source Certificate")
    l10n_mx_edi_cer_source = fields.Char(
        string='Certificate Source',
        help="Used in CFDI like attribute derived from the exception of certificates of Origin of the "
             "Free Trade Agreements that Mexico has celebrated with several countries. If it has a value, it will "
             "indicate that it serves as certificate of origin and this value will be set in the CFDI node "
             "'NumCertificadoOrigen'.")    

    # ==== CFDI attachment fields ====
    cfdi_related_id = fields.Many2one('hr.payslip', string=u'UUID Relacionado', 
        domain=[("state", "!=", "draft"), ("l10n_mx_cfdi_uuid", "!=", None)])
    cfdi_reason_cancel = fields.Selection(
        selection=[
            ('01', u'[01] Comprobante Emitido con errores con relación'),
            ('02', u'[02] Comprobante Emitido con errores sin relación'),
            ('03', u'[03] No se llevo a cabo la operación'),
            ('04', u'[04] Operación nominativa relacionada en una factura global'),
        ],        
        string="CFDI Reason Cancel", copy=False)

    l10n_mx_edi_cfdi_name = fields.Char(string='CFDI name', copy=False, readonly=True,
            help='The attachment name of the CFDI.')    

    l10n_mx_edi_cfdi_uuid_canceled = fields.Char(string='Fiscal Folio Canceled', copy=False, readonly=True)


    l10n_mx_cfdi_uuid = fields.Char(string='Fiscal Folio SAT', copy=False, readonly=True,
        help='Folio in electronic invoice, is returned by SAT when send to stamp.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_uuid = fields.Char(string='Fiscal Folio.', copy=False, readonly=True,
        help='Folio in electronic invoice, is returned by SAT when send to stamp.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_supplier_rfc = fields.Char(string='Supplier RFC', copy=False, readonly=True,
        help='The supplier tax identification number.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_customer_rfc = fields.Char(string='Customer RFC', copy=False, readonly=True,
        help='The customer tax identification number.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_cfdi_amount = fields.Monetary(string='Total Amount', copy=False, readonly=True,
        help='The total amount reported on the cfdi.',
        compute='_compute_cfdi_values')
    l10n_mx_edi_version = fields.Char(string="CFDI version", copy=False, readonly=True, default='4.0')    

    # ==== CFDI attributes ====
    l10n_mx_edi_values = fields.Boolean(
        string="CFDI Email", default=False, 
        compute='_compute_cfdi_attributes')
    cfdi_percepciones_ids = fields.One2many(
        'hr.payslip.line', 'slip_id', string='Percepciones', 
        readonly=True, domain=[('cfdi_tipo_percepcion', '!=', False), ('cfdi_tipo', '=', 'p')])
    cfdi_deducciones_ids = fields.One2many(
        'hr.payslip.line', 'slip_id', string='Deducciones', 
        readonly=True, domain=[('cfdi_tipo_deduccion', '!=', False), ('cfdi_tipo', '=', 'd')])
    cfdi_otrospagos_ids = fields.One2many(
        'hr.payslip.line', 'slip_id', string='Otros Pagos', 
        readonly=True, domain=[('cfdi_tipo_otrospagos', '!=', False), ('cfdi_tipo', '=', 'o')])
    cfdi_incapacidades_ids = fields.One2many(
        'hr.payslip.line', 'slip_id', string='Incapacidades', 
        readonly=True, domain=[('cfdi_tipo_incapacidad', '!=', False), ('cfdi_tipo', '=', 'i')])

    # Percepciones
    cfdi_percepcion_totalexento = fields.Float(string="Total Exento", tracking=True)
    cfdi_percepcion_totalgravado = fields.Float(string="Total Gravado", tracking=True)
    cfdi_percepcion_totalsueldo = fields.Float(string="Total Sueldo", tracking=True)
    cfdi_percepcion_separaciongravado = fields.Float(string="Total Sueldo.", tracking=True)
    cfdi_percepcion_totalseparacionindemnizacion = fields.Float(string="Total Separacion Indemnizacion", tracking=True)
    cfdi_percepcion_totaljubilacionpensiongravado = fields.Float(string="Total Jubilacion Ingreso No Acumulable", tracking=True)
    cfdi_percepcion_totaljubilacionpensionretiro = fields.Float(string="Total Jubilacion Pension Retiro", tracking=True)
    cfdi_percepcion_antiguedad = fields.Float(string="Prima por Antiguedad", help="[022] Prima por Antiguedad", tracking=True)
    cfdi_percepcion_separacion = fields.Float(string="Pagos por separación", help="[023] Pagos por separacion", tracking=True)
    cfdi_percepcion_indemnizacion = fields.Float(string="Indemnizaciones", help="[025] Indemnizaciones", tracking=True)
    cfdi_percepcion_jubilacionretiro = fields.Float(string="Jubilaciones y Retiro", help="[039] Jubilaciones y Retiro", tracking=True)
    cfdi_percepcion_jubilacionretiro_parcial = fields.Float(string="Jubilaciones y Retiro (Parcialidad)", 
        help="[044] Jubilaciones y Retiro Pago en Parcialidades", tracking=True)
    cfdi_percepcion_horasextras = fields.Float(string="Horas Extras", help="[019] Horas Extras", tracking=True)
    
    # Deducciones
    cfdi_deduccion_totalimpuestosret = fields.Float(string="Total Impuestos Retenidos", help="[002] Total Impuestos Retenidos", tracking=True)
    cfdi_deduccion_totalotrasdeducciones = fields.Float(string="Total Otras Deducciones", help="Total Otras Deducciones", tracking=True)
    
    # OtrosPagos
    cfdi_totalotrospagos = fields.Float(string="Total Otros Pagos", help="Total Otros Pagos", tracking=True)
    cfdi_otrospagos_subsidiocausado = fields.Float(string="Subsidio Causado", help="[002] Subsidio Causado", tracking=True)
    cfdi_otrospagos_compensacionsaldosafavor = fields.Float(string="Compensacion Saldos a Favor", 
        help="[004] Compensacion Saldos a Favor", tracking=True)
    
    cfdi_total_percepcion = fields.Float(string="Total Percepcion", help="Total Deduccion", tracking=True)
    cfdi_total_deduccion = fields.Float(string="Total Deduccion", help="Total Percepcion", tracking=True)
    cfdi_descuento = fields.Float(string="Descuento", help="Descuento", tracking=True)
    cfdi_subtotal = fields.Float(string="SubTotal", help="SubTotal", tracking=True)
    cfdi_total = fields.Float(string="Total", help="Total", tracking=True)
    queued_for_pdf = fields.Boolean(default=False)

    payslip_count = fields.Integer(compute='_compute_payslip_count', string="Payslip Computation Details")
    payslip_cancel_count = fields.Integer(compute='_compute_payslip_cancel_count', string="Payslip UUID Details")
    l10n_mx_edi_resigned = fields.Boolean(string="Retimbrado", default=False)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    def _compute_payslip_count(self):
        for payslip in self:
            payslip.payslip_count = len(payslip.line_ids)

    def _compute_payslip_cancel_count(self):
        for payslip in self:
            payslip.payslip_cancel_count = len(self.env['l10n_mx_payroll.uuid.history'].search([('slip_id','=',payslip.id)]))

    # @api.depends('l10n_mx_edi_status')
    def l10n_mx_edi_compute_edi_content(self):
        cfdi_edi_format = self.env.ref('l10n_mx_edi.edi_cfdi_3_3') # TODO no existe en v17
        for payslip in self:
            certificate = payslip.company_id.l10n_mx_edi_certificate_ids.sudo()._get_valid_certificate()
            if not certificate:
                payslip.l10n_mx_edi_content = None
                payslip.l10n_mx_edi_error = None
            else:
                payslip.l10n_mx_edi_content = base64.b64encode(payslip._l10n_mx_edi_create_payslip())

    def _compute_l10n_mx_edi_cancel(self):
        for move in self:
            if move.l10n_mx_edi_cfdi_uuid:
                replaced_move = move.search(
                    [('l10n_mx_edi_origin', 'like', '04|%'),
                     ('l10n_mx_edi_origin', 'like', '%' + move.l10n_mx_edi_cfdi_uuid + '%'),
                     ('company_id', '=', move.company_id.id)],
                    limit=1,
                )
                move.l10n_mx_edi_cancel_invoice_id = replaced_move
            else:
                move.l10n_mx_edi_cancel_invoice_id = None

    def _compute_cfdi_values(self):
        '''Fill the invoice fields from the cfdi values.
        '''
        for move in self:
            cfdi_infos = move._l10n_mx_edi_decode_cfdi()
            move.l10n_mx_cfdi_uuid = cfdi_infos.get('uuid')
            move.l10n_mx_edi_cfdi_uuid = cfdi_infos.get('uuid')
            move.l10n_mx_edi_cfdi_supplier_rfc = cfdi_infos.get('supplier_rfc')
            move.l10n_mx_edi_cfdi_customer_rfc = cfdi_infos.get('customer_rfc')
            move.l10n_mx_edi_cfdi_amount = cfdi_infos.get('amount_total')

    def _compute_cfdi_attributes(self):
        for payslip in self:
            p_lines, d_lines, o_lines = [], [], []
            for line_id in payslip.line_ids:
                if line_id.cfdi_tipo == 'p' and line_id.total > 0:
                    p_lines.append( line_id )
                elif line_id.cfdi_tipo == 'd' and line_id.total != 0:
                    d_lines.append( line_id )
                elif line_id.cfdi_tipo == 'o':
                    o_lines.append( line_id )

            # _logger.info('----- P %s D %s O %s'%( len(p_lines), len(d_lines), len(o_lines) ) )
            hora_extra, subtotal, descuento, total = 0, 0, 0, 0
            gravado, exento, antiguedad, separacion, indemnizacion, jubilacionretiro, jubilacionretiro_parcial, totalsueldo, totaljubilacionpensiongravado, separaciongravado = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
            impretenidos, otrasdeduc = 0, 0
            otrospagos, subsidiocausado, saldoafavor, incapacidad = 0, 0, 0, 0

            for pline in p_lines:
                gravado += pline.total_gravado
                exento += pline.total_exento
                # SeparacionIndemnizacion
                if pline.cfdi_tipo_percepcion == '022':
                    antiguedad += pline.total
                    separaciongravado += pline.total_gravado
                if pline.cfdi_tipo_percepcion == '023':
                    antiguedad += pline.total
                    separaciongravado += pline.total_gravado
                if pline.cfdi_tipo_percepcion == '025':
                    indemnizacion += pline.total
                    separaciongravado += pline.total_gravado
                # JubilacionPensionRetiro
                if pline.cfdi_tipo_percepcion == '039':
                    jubilacionretiro += pline.total
                    totaljubilacionpensiongravado += pline.total_gravado
                if pline.cfdi_tipo_percepcion == '044':
                    jubilacionretiro_parcial += pline.total
                    totaljubilacionpensiongravado += pline.total_gravado
                if pline.cfdi_tipo_percepcion not in ['022', '023', '025', '039', '044']:
                    totalsueldo += pline.total
                if pline.cfdi_tipo_percepcion == '019':
                    hora_extra = pline.total_gravado + pline.total_exento
            
            for dline in d_lines:
                if dline.cfdi_tipo_deduccion == '002':
                    impretenidos += dline.total
                else:
                    otrasdeduc += dline.total
            
            for oline in o_lines:
                if oline.total == 0 and oline.cfdi_tipo_otrospagos != '002':
                    continue
                if oline.cfdi_tipo_otrospagos == '002':
                    subsidiocausado += oline.total
                if oline.cfdi_tipo_otrospagos == '004':
                    saldoafavor += oline.total
                otrospagos += abs(oline.total)
            vals = {
                'cfdi_percepcion_antiguedad': antiguedad,
                'cfdi_percepcion_separacion': separacion,
                'cfdi_percepcion_indemnizacion': indemnizacion, 
                'cfdi_percepcion_totalsueldo': totalsueldo,
                'cfdi_percepcion_separaciongravado': separaciongravado,
                'cfdi_percepcion_totalseparacionindemnizacion': (antiguedad + separacion + indemnizacion),

                'cfdi_percepcion_jubilacionretiro': jubilacionretiro,
                'cfdi_percepcion_jubilacionretiro_parcial': jubilacionretiro_parcial,
                'cfdi_percepcion_totaljubilacionpensionretiro': (jubilacionretiro + jubilacionretiro_parcial),
                'cfdi_percepcion_totaljubilacionpensiongravado': totaljubilacionpensiongravado,

                'cfdi_percepcion_totalgravado': gravado,
                'cfdi_percepcion_totalexento': exento,
                'cfdi_percepcion_horasextras': hora_extra,
                'cfdi_deduccion_totalimpuestosret': abs(impretenidos),
                'cfdi_deduccion_totalotrasdeducciones': abs(otrasdeduc),
                'cfdi_totalotrospagos': otrospagos,
                'cfdi_otrospagos_subsidiocausado': subsidiocausado,
                'cfdi_otrospagos_compensacionsaldosafavor': saldoafavor
            }
            vals['cfdi_total_percepcion'] = vals['cfdi_percepcion_totalsueldo'] + vals['cfdi_percepcion_totalseparacionindemnizacion'] + vals['cfdi_percepcion_totaljubilacionpensionretiro']
            vals['cfdi_total_deduccion'] = vals['cfdi_deduccion_totalotrasdeducciones'] + vals['cfdi_deduccion_totalimpuestosret']
            vals['cfdi_subtotal'] = vals['cfdi_total_percepcion'] + vals['cfdi_totalotrospagos']
            vals['cfdi_descuento'] = vals['cfdi_total_deduccion']
            vals['cfdi_total'] = vals['cfdi_subtotal'] - abs(vals['cfdi_descuento'])
            payslip.update(vals)
        return {}

    # -------------------------------------------------------------------------
    # BASE METHODS
    # -------------------------------------------------------------------------
    def unlink(self):
        if any(payslip.l10n_mx_cfdi_uuid for payslip in self):
            raise UserError(_('¡No puede eliminar un recibo de nómina que haya sido timbrado!'))
        return super(HrPayslip, self).unlink()

    def write(self, vals):
        res = super(HrPayslip, self).write(vals)
        return res

    def _get_localdict(self):
        self.ensure_one()
        localdict = {
            **super(HrPayslip, self)._get_localdict(),
            **{'gravex': DefaultDictPayroll(lambda: dict(total_gravado=0, total_exento=0, dias_incapacidad=0)),}
        }
        #localdict['gravex'] = BrowsableObject(self.employee_id.id, {}, self.env)
        return localdict

    def _get_payslip_lines(self):
        lines = super(HrPayslip, self)._get_payslip_lines()
        context = dict(self.env.context)
        cfdi_nomina = context.get('cfdi_nomina', {})
        ruleModel = self.env['hr.salary.rule']
        fields = ['cfdi_tipo','cfdi_tipo_percepcion','cfdi_tipo_deduccion','cfdi_tipo_otrospagos','cfdi_tipo_incapacidad','cfdi_codigoagrupador', 'cfdi_tipo_neg','cfdi_tipo_percepcion_neg','cfdi_tipo_deduccion_neg','cfdi_tipo_otrospagos_neg','cfdi_tipo_incapacidad_neg','cfdi_codigoagrupador_neg']
        for line in lines:
            rule_ids = ruleModel.search_read([('id', '=', line.get('salary_rule_id'))], fields)
            total = float(line.get('quantity')) * line.get('amount') * line.get('rate') / 100
            importes = cfdi_nomina.get( line['salary_rule_id'], {} )
            vals = {}
            if total >= 0:
                for rule_id in rule_ids:
                    vals = {
                        'cfdi_tipo': rule_id.get('cfdi_tipo'),
                        'cfdi_tipo_percepcion': rule_id.get('cfdi_tipo_percepcion'),
                        'cfdi_tipo_deduccion': rule_id.get('cfdi_tipo_deduccion'),
                        'cfdi_tipo_otrospagos': rule_id.get('cfdi_tipo_otrospagos'),
                        'cfdi_tipo_incapacidad': rule_id.get('cfdi_tipo_incapacidad'),
                        'cfdi_codigoagrupador': rule_id.get('cfdi_codigoagrupador'),
                        'total_exento': importes.get('total_exento', 0.0),
                        'total_gravado': importes.get('total_gravado', 0.0),
                        'dias_incapacidad': importes.get('dias_incapacidad', 0.0)
                    }
            elif total < 0:
                for rule_id in rule_ids:
                    vals = {
                        'cfdi_tipo': rule_id.get('cfdi_tipo_neg'),
                        'cfdi_tipo_percepcion': rule_id.get('cfdi_tipo_percepcion_neg'),
                        'cfdi_tipo_deduccion': rule_id.get('cfdi_tipo_deduccion_neg'),
                        'cfdi_tipo_otrospagos': rule_id.get('cfdi_tipo_otrospagos_neg'),
                        'cfdi_tipo_incapacidad': rule_id.get('cfdi_tipo_incapacidad_neg'),
                        'cfdi_codigoagrupador': rule_id.get('cfdi_codigoagrupador_neg'),
                        'total_exento': importes.get('total_exento', 0.0),
                        'total_gravado': importes.get('total_gravado', 0.0),
                        'dias_incapacidad': importes.get('dias_incapacidad', 0.0)
                    }
            line.update(vals)
        return lines

    def compute_sheet(self):
        res = super(HrPayslip, self).compute_sheet()
        return res

    def action_payslip_done(self):
        ctx = dict(self.env.context)
        ctx.pop('payslip_generate_pdf', None)
        self.env.context = ctx
        for payslip in self:
            payslip.l10n_mx_edi_xmlcfdi = False
            certificate = payslip.company_id.l10n_mx_edi_certificate_ids.sudo()._get_valid_certificate()
            if payslip.state == 'cancel':
                continue
            if payslip.cfdi_total <= 0:
                res = super(HrPayslip, payslip).action_payslip_done()
                payslip.message_post(body=_("No es necesario timbrar este recibo porque el Total es 0.0 "),)
            elif not certificate:
                res = super(HrPayslip, payslip).action_payslip_done()
            elif not payslip.l10n_mx_edi_cfdi_uuid and payslip.cfdi_total > 0:
                res = payslip.action_cfdi_nomina_generate()
            _logger.info('--- MDM action_payslip_done uuid: %s'% payslip.name )  # ._l10n_mx_edi_decode_cfdi().get('uuid'))

        return True

    """
    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        res = super()._onchange_employee()
        if self.payslip_run_id.struct_id:
            lang = self.employee_id.sudo().address_home_id.lang or self.env.user.lang
            context = {'lang': lang}
            self.struct_id = self.payslip_run_id.struct_id
            payslip_name = self.struct_id.payslip_name or _('Salary Slip')
            self.name = '%s - %s - %s' % (
                payslip_name,
                self.employee_id.name or '',
                format_date(self.env, self.date_from, date_format="MMMM y", lang_code=lang)
            )
    """

    def _l10n_mx_edi_decode_cfdi(self, cfdi_data=None):
        ''' Helper to extract relevant data from the CFDI to be used, for example, when printing the picking.
        TODO replace this function in l10n_mx_edi.account_move with a reusable model method
        :param cfdi_data:   The optional cfdi data.
        :return:            A python dictionary.
        '''
        self.ensure_one()

        # Get the signed cfdi data.
        if not cfdi_data:
            cfdi_data = self.l10n_mx_edi_cfdi_file_id.raw

        # Nothing to decode.
        if not cfdi_data:
            return {}

        try:
            cfdi_node = objectify.fromstring(cfdi_data)
        except etree.XMLSyntaxError:
            # Not an xml
            return {}

        return self.env["account.move"]._l10n_mx_edi_decode_cfdi_etree(cfdi_node)    

    # -------------------------------------------------------------------------
    # BUTTONS METHODS
    # -------------------------------------------------------------------------
    def l10n_mx_edi_export_invoice_cfdi(self):
        return self.l10n_mx_edi_export_test_invoice_cfdi()  
    
    def l10n_mx_edi_export_test_invoice_cfdi(self):
        for payslip in self:
            return payslip.l10n_mx_edi_action_download()

    def l10n_mx_edi_action_clear_error(self):
        for record in self:
            record.l10n_mx_edi_error = False

    def l10n_mx_edi_action_download(self):
        self.ensure_one()
        # self.l10n_mx_edi_compute_edi_content()
        return {
            'type': 'ir.actions.act_url',
            'url':  '/cfdi/downloadxml/%s' % self.id,
        }

    def button_cancel_xml(self):
        ctx = self.env.context.copy()
        for payslip in self:
            reason_cancel = ctx.get('reason_cancel',False)
            if not reason_cancel:
                action = self.env.ref('l10n_mx_payslip.hr_payslip_reason_cancel_action').read([])[0]
                ctx.update({
                    'reason_cancel':payslip.cfdi_reason_cancel,
                    'readonly':True, 
                    'uuid':payslip.l10n_mx_edi_cfdi_uuid,
                    'to_cancel':payslip.l10n_mx_edi_cfdi_uuid_canceled,
                    'slip_id': payslip.id
                })
                action['context'] = ctx
                return action
            if ctx.get('reason_cancel',False) == '01':
                uuid = payslip.l10n_mx_edi_cfdi_uuid_canceled
            else:
                uuid = payslip.payslip.l10n_mx_edi_cfdi_uuid
            val = {
                'cfdi_reason_cancel': reason_cancel,
                'l10n_mx_edi_version': payslip.l10n_mx_edi_version,
                'l10n_mx_edi_sat_status': payslip.l10n_mx_edi_sat_status,
                'l10n_mx_edi_post_time': payslip.l10n_mx_edi_post_time,
                'l10n_mx_edi_cfdi_uuid': uuid,
                'l10n_mx_edi_cfdi_customer_rfc': payslip.l10n_mx_edi_cfdi_customer_rfc,
                'l10n_mx_edi_status': payslip.l10n_mx_edi_status,
                'invoice_date': payslip.invoice_date,
                'l10n_mx_edi_cfdi_supplier_rfc': payslip.l10n_mx_edi_cfdi_supplier_rfc,
                'l10n_mx_edi_cfdi_amount': payslip.l10n_mx_edi_cfdi_amount,
                'slip_id': payslip.id,
            }
            self.env['l10n_mx_payroll.uuid.history'].create(val)
            payslip.write({
                'l10n_mx_edi_resigned': False,
            })
            payslip.action_payslip_cancel()        

    def button_resign_xml(self):
        ctx = self.env.context.copy()
        for payslip in self:
            reason_cancel = ctx.get('reason_cancel',False) # or payslip.cfdi_reason_cancel
            if not reason_cancel:
                action = self.env.ref('l10n_mx_payslip.hr_payslip_reason_cancel_action').read([])[0]
                ctx.update({'reason_cancel':payslip.cfdi_reason_cancel, 'slip_id': payslip.id})
                action['context'] = ctx
                return action
            payslip.write({
                'cfdi_reason_cancel': reason_cancel,
                'l10n_mx_edi_resigned': True,
                'l10n_mx_edi_cfdi_uuid_canceled': payslip.l10n_mx_edi_cfdi_uuid,
                'l10n_mx_edi_cfdi_uuid': False,
                'l10n_mx_cfdi_uuid': False,
                'l10n_mx_edi_post_time': False,
                'invoice_date': False,
                'l10n_mx_edi_origin': '04|%s'%payslip.l10n_mx_edi_cfdi_uuid,
            })
            payslip.action_payslip_done()

    def set_l10n_mx_edi_post_time(self):
        issued_address = self._get_l10n_mx_edi_issued_address()
        date_fmt = '%Y-%m-%dT%H:%M:%S'
        mx_tz = self.env['account.move']._l10n_mx_edi_get_cfdi_partner_timezone(issued_address or self.company_id.partner_id)
        certificate_date = self.env['l10n_mx_edi.certificate'].sudo().get_mx_current_datetime()
        try:
            self.l10n_mx_edi_post_time = fields.Datetime.to_string(datetime.now(mx_tz))
            self.invoice_date = certificate_date.date()
        except Exception as e:
            _logger.info("------ Payroll Error %s "%(e) )


    # -------------------------------------------------------------------------
    # CFDI: Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _getRemoverAcentos(remover=''):
        return remove_accents( remover )

    @staticmethod
    def _getMayusculas(palabras=''):
        return palabras.upper()

    def _getCompanyName(self):
        companyName = ''
        rp = self.employee_id.cfdi_registropatronal_id and self.employee_id.cfdi_registropatronal_id.address_id or False
        if rp:
            companyName = rp.street_name if rp.street_name else ''
            if rp.street_number:
                companyName += ' %s'%rp.street_number
            if rp.l10n_mx_edi_colony:
                companyName += ' COL. %s'%rp.l10n_mx_edi_colony
            if rp.zip:
                companyName += '  %s'%rp.zip
            if rp.city:
                companyName += '  %s'%rp.city
            if rp.state_id:
                companyName += '  %s'%rp.state_id.name
        return companyName.upper()

    def _get_RegistroPatronal(self):
        rp = self.employee_id.cfdi_registropatronal_id and self.employee_id.cfdi_registropatronal_id.code or False
        if rp == False:
            rp = self.company_id.cfdi_registropatronal_id and self.company_id.cfdi_registropatronal_id.code or ''
        return rp

    def _get_NumDiasPagados(self):
        if not self.struct_id:
            return ''
        dias = self._get_salary_line_total('C9') or 0.0
        if self.struct_id and self.struct_id.l10n_mx_edi_tiponominaespecial in ['ext_fini', 'ext_nom', 'ext_agui']:
            dias = 1.0
        return "%d"%dias

    @api.model
    def _l10n_mx_edi_cfdi_amount_to_text(self, amount=0.0):
        """Method to transform a float amount to text words
        E.g. 100 - ONE HUNDRED
        :returns: Amount transformed to words mexican format for invoices
        :rtype: str
        """
        self.ensure_one()
        currency_name = self.currency_id.name.upper()
        # M.N. = Moneda Nacional (National Currency)
        # M.E. = Moneda Extranjera (Foreign Currency)
        currency_type = 'M.N' if currency_name == 'MXN' else 'M.E.'
        # Split integer and decimal part
        amount_i, amount_d = divmod(amount, 1)
        amount_d = round(amount_d, 2)
        amount_d = int(round(amount_d * 100, 2))
        words = self.currency_id.with_context(lang=self.company_id.partner_id.lang or 'es_MX').amount_to_text(amount_i).upper()
        return '%(words)s %(amount_d)02d/100 %(currency_type)s' % {
            'words': words,
            'amount_d': amount_d,
            'currency_type': currency_type,
        }

    @api.model
    def _l10n_mx_edi_cfdi_qr(self):
        self.ensure_one()
        cfdi_infos = self._l10n_mx_edi_decode_cfdi()
        barcode_value_params = keep_query(
            id=cfdi_infos['uuid'],
            re=cfdi_infos['supplier_rfc'],
            rr=cfdi_infos['customer_rfc'],
            tt=cfdi_infos['amount_total'],
        )
        barcode_sello = url_quote_plus(cfdi_infos['sello'][-8:], safe='=/').replace('%2B', '+')
        barcode_value = url_quote_plus(f'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?{barcode_value_params}&fe={barcode_sello}')
        barcode_src = f'/report/barcode/?barcode_type=QR&value={barcode_value}&width=180&height=180'
        return barcode_src

    @api.model
    def _l10n_mx_edi_check_configuration(self):
        company = self.company_id
        pac_name = company.l10n_mx_edi_pac
        errors = []
        # == Check the certificate ==
        certificate = company.l10n_mx_edi_certificate_ids.sudo()._get_valid_certificate()
        if not certificate:
            errors.append(_('No valid certificate found'))

        # == Check the credentials to call the PAC web-service ==
        if pac_name:
            pac_test_env = company.l10n_mx_edi_pac_test_env
            pac_password = company.l10n_mx_edi_pac_password
            if not pac_test_env and not pac_password:
                errors.append(_('No PAC credentials specified.'))
        else:
            errors.append(_('No PAC specified.'))
        return errors

    # -------------------------------------------------------------------------
    # XML
    # -------------------------------------------------------------------------
    def _get_report_base_filename(self):
        return 'NOM-%s - %s' % ( (self.number or '').replace('/',''), self.employee_id.display_name)

    def _l10n_mx_edi_get_cadena_xslt(self):
        return 'l10n_mx_edi_40/data/4.0/cadenaoriginal_4_0.xslt'

    def _l10n_mx_edi_dg_render(self, values):
        return self.env['ir.qweb']._render('l10n_mx_payslip.cfdipayslipv40', values)

    def _l10n_mx_edi_create_xml_payslip(self):
        self.ensure_one()
        cfdi_edi_format = self.env.ref('l10n_mx_edi.edi_cfdi_3_3') # TODO no existe en v17
        cfdi_values = cfdi_edi_format.l10n_mx_edi_get_payslip_cfdi_values(self)
        xml = self._l10n_mx_edi_dg_render(cfdi_values)
        certificate = self.company_id.l10n_mx_edi_certificate_ids.sudo()._get_valid_certificate()
        if certificate:
            xml = certificate._certify_and_stamp(xml, self._l10n_mx_edi_get_cadena_xslt())
        xml = b' '.join(xml.split())
        self.l10n_mx_edi_content = base64.b64encode(xml)
        _logger.info("xml=%s"%xml.decode("utf-8") )
        return xml

    def _get_l10n_mx_edi_issued_address(self):
        self.ensure_one()
        return self.company_id.partner_id.commercial_partner_id

    def l10n_mx_edi_get_common_cfdi_values(self):
        localdict = self.env.context.get('force_payslip_localdict', None)
        if localdict is None:
            localdict = self._get_localdict()
        rules_dict = localdict['rules'].dict
        result_rules_dict = localdict['result_rules'].dict
        payslip_dict = localdict['payslip'].dict
        blacklisted_rule_ids = self.env.context.get('prevent_payslip_computation_line_ids', [])
        for rule in sorted(self.struct_id.rule_ids, key=lambda x: x.sequence):
            if rule.id in blacklisted_rule_ids:
                continue
            localdict.update({
                'result': None,
                'result_qty': 1.0,
                'result_rate': 100})
            if rule._satisfy_condition(localdict):
                amount, qty, rate = rule._compute_rule(localdict)
                #check if there is already a rule computed with that code
                previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                #set/overwrite the amount computed for this rule in the localdict
                tot_rule = amount * qty * rate / 100.0
                localdict[rule.code] = tot_rule
                result_rules_dict[rule.code] = {'total': tot_rule, 'amount': amount, 'quantity': qty}
                rules_dict[rule.code] = rule
                # sum the amount for its salary category
                localdict = rule.category_id._sum_salary_rule_category(localdict, tot_rule - previous_amount)
        employee = self.employee_id
        xmldatas = DefaultDictPayroll(lambda: 0) #BrowsableObject(employee.id, {}, self.env)
        localdict['xmldatas'] = xmldatas
        localdict['datetime'] = datetime
        localdict['relativedelta'] = relativedelta
        # export_ids = self.env["edi.data.configuration.xml"].search([('company_id', '=', self.company_id.id), ('model_name', '=', 'hr.payslip')], limit=1)
        XMLConfig = self.env["edi.data.configuration.xml"].with_user(self.env.user).sudo()
        export_ids = XMLConfig.search([('model_name', '=', 'hr.payslip')], limit=1)
        for export_id in export_ids:
            res = export_id.compute_export_data( localdict )
            res['employee'] = localdict['employee']
            res['contract'] = localdict['contract']
            return res
        return {}        

    def l10n_mx_edi_action_update_sat_status(self):
        '''Synchronize both systems: Odoo & SAT to make sure the delivery guide is valid.
        '''
        for record in self:
            decoded_cfdi = record._l10n_mx_edi_decode_cfdi()
            supplier_rfc = record.company_id.vat
            customer_rfc = record.partner_id.commercial_partner_id.vat
            total = decoded_cfdi.get('amount_total', 0.0)
            uuid = decoded_cfdi.get('uuid', False)
            try:
                status = self.env['account.edi.format']._l10n_mx_edi_get_sat_status(supplier_rfc, customer_rfc, total, uuid)
            except Exception as e:
                record._message_log(body=_("Failure during update of the SAT status: %(msg)s", msg=e))
                continue
            if status == 'Vigente':
                record.l10n_mx_edi_sat_status = 'valid'
            elif status == 'Cancelado':
                record.l10n_mx_edi_sat_status = 'cancelled'
            elif status == 'No Encontrado':
                record.l10n_mx_edi_sat_status = 'not_found'
            else:
                record.l10n_mx_edi_sat_status = 'none'

    def _get_l10n_mx_edi_signed_edi_document(self):
        self.ensure_one()
        return self.l10n_mx_edi_cfdi_file_id or None

    @api.model
    def l10n_mx_edi_retrieve_attachments(self): # 'SLIP216616-AA4211C0-792F-4521-9926-FD66746551A4-MX-Payslip-4.0.xml'
        self.ensure_one()
        to_cancel_uuid = self._context.get('to_cancel_uuid')
        version = self.l10n_mx_edi_version
        domain = [
            ('res_id', '=', self.id),
            ('res_model', '=', self._name),
        ]
        if version == '4.0':
            if to_cancel_uuid:
                uuid = to_cancel_uuid
                cfdi_filename = ('%s-%s-MX-Payslip-%s.xml' % (self.number, uuid, version)).replace('/', '')
            elif not self.l10n_mx_edi_cfdi_name:
                uuid = self.l10n_mx_edi_cfdi_uuid
                cfdi_filename = ('%s-%s-MX-Payslip-%s.xml' % (self.number, uuid, version)).replace('/', '')
                self.l10n_mx_edi_cfdi_name = cfdi_filename
            else:
                cfdi_filename = self.l10n_mx_edi_cfdi_name
            domain.append( ('name', '=', cfdi_filename) )
        else:
            cfdi_filename = ('%MX-Payslip-3.3.xml')
            domain.append(('name', 'like', cfdi_filename))
        return self.env['ir.attachment'].search(domain)        

    # -------------------------------------------------------------------------
    # BUSINESS METHODS - CFDI
    # -------------------------------------------------------------------------
    @api.model
    def _payroll_send_email_cfdi(self, batch_size=False):
        ctx = self.env.context
        template = self.env.ref('hr_payroll.mail_template_new_payslip', raise_if_not_found=False)        
        payslips = self.search([
            ('state', '=', 'done'),
            ('l10n_mx_edi_sendemail', '=', False),
            ('payslip_run_id.l10n_mx_edi_sendemail', '=', True)
        ], limit=1)
        for payslip in payslips:
            mail_id = template.send_mail(payslip.id, email_layout_xmlid='mail.mail_notification_light')
            if mail_id:
                payslip.l10n_mx_edi_sendemail = True
        if len(payslips) == 1:  # assumes there are more whenever search hits limit
            trigger = self.env.ref('l10n_mx_payslip.ir_cron_payroll_send_email_cfdi')
            trigger.sudo().method_direct_trigger()            



    @api.model
    def _payroll_generate_xml_cfdi(self, batch_size=False):
        ctx = self.env.context
        payslips = self.search([
            ('state', '=', 'verify'),
            ('l10n_mx_edi_xmlcfdi', '=', True),
        ], limit=1)
        try:
            with self.env.cr.savepoint():
                payslips.action_payslip_done()
        except Exception as e:
            for payslip in payslips:
                try:
                    with self.env.cr.savepoint():
                        payslip.action_payslip_done()
                except Exception as e:
                    payslip.l10n_mx_edi_xmlcfdi = False
                    msg = _('The payslip could not be posted for the following reason: %(error_message)s', error_message=e)
                    payslip.message_post(body=msg, message_type='comment')
        if len(payslips) == 1:  # assumes there are more whenever search hits limit
            trigger = self.env.ref('l10n_mx_payslip.ir_cron_payroll_generate_xml_cfdi')
            trigger.sudo().method_direct_trigger()

    def action_cfdi_nomina_generate(self):
        EdiFormat = self.env["account.edi.format"]
        for record in self:
            pac_name = record.company_id.l10n_mx_edi_pac

            credentials = getattr(EdiFormat, '_l10n_mx_edi_get_%s_credentials' % pac_name)(record.company_id)
            if credentials.get('errors'):
                record.l10n_mx_edi_error = '\n'.join(credentials['errors'])
                continue

            cfdi_str = record._l10n_mx_edi_create_xml_payslip()
            res = getattr(EdiFormat, '_l10n_mx_edi_%s_sign' % pac_name)(credentials, cfdi_str)
            if res.get('errors'):
                record.l10n_mx_edi_error = '\n'.join(res['errors'])
                continue

            # == Create the attachment ==
            cfdi_signed = base64.decodebytes(res['cfdi_signed']) if res['cfdi_encoding'] == 'base64' else res['cfdi_signed']
            uuid = record._l10n_mx_edi_decode_cfdi(cfdi_signed).get('uuid')
            cfdi_attachment = self.env['ir.attachment'].create({
                'name': ATTACHMENT_NAME.format(uuid),
                'res_id': record.id,
                'res_model': record._name,
                'type': 'binary',
                'raw': cfdi_signed,
                'mimetype': 'application/xml',
                'description': _('Mexican Payroll CFDI generated for the %s document.', record.name),
            })
            record.l10n_mx_edi_cfdi_file_id = cfdi_attachment.id

            message = _("The CFDI Payroll has been successfully signed.")
            record._message_log(body=message, attachment_ids=cfdi_attachment.ids)
            record.write({'state' : 'done', 'l10n_mx_edi_cfdi_uuid': uuid, 'l10n_mx_edi_error': False, 'l10n_mx_edi_status': 'sent'})















































    # -------------------------------------------------------------------------
    # CFDI: Helpers
    # -------------------------------------------------------------------------
    def _l10n_mx_edi_get_cadena_xslts_old(self):
        version = self.l10n_mx_edi_version
        if version == '3.3':
            return CFDI_XSLT_CADENA_TFD, CFDI_XSLT_CADENA
        return 'l10n_mx_edi_40/data/4.0/cadenaoriginal_TFD_1_1.xslt', 'l10n_mx_edi_40/data/4.0/cadenaoriginal_4_0.xslt'

    @api.model
    def _l10n_mx_edi_format_error_message_old(self, error_title, errors):
        bullet_list_msg = ''.join('<li>%s</li>' % msg for msg in errors)
        body = bullet_list_msg.replace(""":1:0:ERROR:SCHEMASV:SCHEMAV_CVC_COMPLEX_TYPE_4: Element '{http://www.sat.gob.mx/nomina12}""", "'")
        body = body.replace(""":1:0:ERROR:SCHEMASV:SCHEMAV_CVC_MINLENGTH_VALID: Element '{http://www.sat.gob.mx/nomina12}""", "'")
        body = body.replace(""":1:0:ERROR:SCHEMASV:SCHEMAV_CVC_PATTERN_VALID: Element '{http://www.sat.gob.mx/nomina12}""", "'")
        body = body.replace(""":1:0:ERROR:SCHEMASV:SCHEMAV_CVC_MININCLUSIVE_VALID: Element '{http://www.sat.gob.mx/nomina12}""", "'")
        body = body.replace(""":1:0:ERROR:SCHEMASV:SCHEMAV_ELEMENT_CONTENT: Element: '{http://www.sat.gob.mx/nomina12}""", "'")
        body = body.replace(""":1:0:ERROR:SCHEMASV:SCHEMAV_CVC_COMPLEX_TYPE_4: Element '{http://www.sat.gob.mx/cfd/3}""", "'")
        body = body.replace(""":1:0:ERROR:SCHEMASV:SCHEMAV_CVC_MININCLUSIVE_VALID: Element '{http://www.sat.gob.mx/cfd/3}""", "'")
        body = body.replace(""":1:0:ERROR:SCHEMASV:SCHEMAV_CVC_PATTERN_VALID: Element '{http://www.sat.gob.mx/cfd/3}""", '')
        body = body.replace(""":1:0:ERROR:SCHEMASV:SCHEMAV_CVC_DATATYPE_VALID_1_2_1: Element '{http://www.sat.gob.mx/cfd/3}""", "'")
        body = body.replace(""":1:0:ERROR:SCHEMASV:SCHEMAV_CVC_COMPLEX_TYPE_4: Element '{http://www.sat.gob.mx/cfd/3}""", "'")
        body = body.replace("<string>", "<br />")
        return '%s<ul>%s</ul>' % (error_title, body)



    def _get_report_base_filename_old(self):
        return 'NOM-%s - %s' % ( (self.number or '').replace('/',''), self.employee_id.display_name)

    @api.model
    def _l10n_mx_edi_get_serie_and_folio_old(self):
        if not self.number:
            return {
                'serie_number': '',
                'folio_number': '',
            }
        payslip_number = (self.number or '').replace('/', '').replace('-', '')
        name_numbers = list(re.finditer('\d+', payslip_number))
        serie_number = payslip_number[:name_numbers[-1].start()]
        folio_number = name_numbers[-1].group().lstrip('0')
        return {
            'serie_number': serie_number,
            'folio_number': folio_number,
        }



    # -------------------------------------------------------------------------
    # BUSINESS METHODS - CFDI
    # -------------------------------------------------------------------------
    @api.model
    def _l10n_mx_edi_get_cfdi_partner_timezone_old(self, partner):
        code = partner.state_id.code
        # northwest area
        if code == 'BCN':
            return timezone('America/Tijuana')
        # Southeast area
        elif code == 'ROO':
            return timezone('America/Cancun')
        # Pacific area
        elif code in ('BCS', 'CHH', 'SIN', 'NAY'):
            return timezone('America/Chihuahua')
        # Sonora
        elif code == 'SON':
            return timezone('America/Hermosillo')
        # By default, takes the central area timezone
        return timezone('America/Mexico_City')



    @api.model
    def _l10n_mx_edi_read_cfdi_origin_old(self, cfdi_origin):
        splitted = cfdi_origin.split('|')
        if len(splitted) != 2:
            return False
        try:
            code = int(splitted[0])
        except ValueError:
            return False
        if code < 1 or code > 7:
            return False
        return splitted[0], [uuid.strip() for uuid in splitted[1].split(',')]













       

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    def _l10n_mx_edi_create_payslip_cfdi_old(self):
        # == CFDI values ==
        cfdi_edi_format = self.env.ref('l10n_mx_edi.edi_cfdi_3_3') # TODO no existe en v17
        for payslip in self:
            res = cfdi_edi_format._l10n_mx_edi_export_payslip_cfdi(payslip)
            if res.get('errors'):
                payslip.message_post(
                    body='%s'%( payslip._l10n_mx_edi_format_error_message(_("Invalid configuration:"), res['errors']) )
                )
                return ''
            else:
                return '%s'%(res.get('cfdi_str').decode("utf-8"))

    def action_cfdi_nomina_generate_old(self):
        cfdi_edi_format = self.env.ref('l10n_mx_edi.edi_cfdi_3_3') # TODO no existe en v17
        edi_result = {}
        for payslip in self:
            version = payslip.l10n_mx_edi_version
            payslip.write({
                'l10n_mx_edi_status': 'to_send',
                'l10n_mx_edi_sat_status': 'none',
            })

            errors = payslip._l10n_mx_edi_check_configuration()
            if errors:
                msg = payslip._l10n_mx_edi_format_error_message(_("Invalid configuration:"), errors)
                edi_result[payslip.id] = {'error': mgs,}
                payslip.l10n_mx_edi_error = msg
                continue

            # CFDI Productivo
            pac_name = payslip.company_id.l10n_mx_edi_pac
            credentials = getattr(cfdi_edi_format, '_l10n_mx_edi_get_%s_credentials_company' % pac_name)(payslip.company_id)
            if credentials.get('errors'):
                msg = payslip._l10n_mx_edi_format_error_message(_("PAC authentification error:"), credentials['errors'])
                edi_result[payslip.id] = {'error': msg,}
                payslip.l10n_mx_edi_error = msg
                continue

            # == Generate the CFDI ==
            res = cfdi_edi_format._l10n_mx_edi_export_payslip_cfdi(payslip)
            if res.get('errors'): 
                msg = payslip._l10n_mx_edi_format_error_message(_("Failure during the generation of the CFDI:"), res['errors'])
                payslip.l10n_mx_edi_error = msg
                edi_result[payslip.id] = {'error': msg,}
                continue

            # == Call the web-service ==
            res = getattr(cfdi_edi_format, '_l10n_mx_edi_%s_sign_service' % pac_name)(credentials, res['cfdi_str'])
            if res.get('errors'):
                msg = payslip._l10n_mx_edi_format_error_message(_("PAC failed to sign the CFDI:"), res['errors'])
                payslip.l10n_mx_edi_error = '\n'.join(res['errors'])
                edi_result[payslip.id] = {'error': msg,}
                continue

            # == Create the attachment ==
            cfdi_signed = base64.decodebytes(res['cfdi_signed']) if res['cfdi_encoding'] == 'base64' else res['cfdi_signed']
            uuid = payslip._l10n_mx_edi_decode_cfdi(cfdi_signed).get('uuid')
            cfdi_filename = ('%s-%s-MX-Payslip-%s.xml' % (payslip.number, uuid, version)).replace('/', '')
            payslip.l10n_mx_edi_cfdi_name = cfdi_filename
            cfdi_attachment = self.env['ir.attachment'].create({
                'name': cfdi_filename,
                'res_id': payslip.id,
                'res_model': payslip._name,
                'type': 'binary',
                'raw': cfdi_signed,
                'mimetype': 'application/xml',
                'description': _('Mexican Payroll CFDI generated for the %s document.', payslip.name),
            })
            payslip.l10n_mx_edi_cfdi_file_id = cfdi_attachment.id
            edi_result[payslip.id] = {'attachment': cfdi_attachment}

            # == Chatter ==
            message = _("The CFDI Payslip has been successfully signed.")
            payslip._message_log(body=message, attachment_ids=cfdi_attachment.ids)
            payslip.write({'state' : 'done', 'l10n_mx_edi_cfdi_uuid': uuid, 'l10n_mx_edi_error': False, 'l10n_mx_edi_status': 'sent'})
            payslip.with_context(payslip_generate_pdf=True).action_payslip_done_post()

    def action_payslip_done_post_old(self):
        self.mapped('payslip_run_id').action_close()
        # Validate work entries for regular payslips (exclude end of year bonus, ...)
        regular_payslips = self.filtered(lambda p: p.struct_id.type_id.default_struct_id == p.struct_id)
        work_entries = self.env['hr.work.entry']
        for regular_payslip in regular_payslips:
            work_entries |= self.env['hr.work.entry'].search([
                ('date_start', '<=', regular_payslip.date_to),
                ('date_stop', '>=', regular_payslip.date_from),
                ('employee_id', '=', regular_payslip.employee_id.id),
            ])
        if work_entries:
            work_entries.action_validate()

        if self.env.context.get('payslip_generate_pdf'):
            if self.env.context.get('payslip_generate_pdf_direct'):
                self._generate_pdf()
            else:
                self.write({'queued_for_pdf': True})
                payslip_cron = self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs', raise_if_not_found=False)
                if payslip_cron:
                    payslip_cron._trigger()

    def _get_pdf_reports_old(self):
        classic_report = self.env.ref('hr_payroll.action_report_payslip')
        result = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in self:
            if not payslip.struct_id or not payslip.struct_id.report_id:
                result[classic_report] |= payslip
            else:
                result[payslip.struct_id.report_id] |= payslip
        return result

    def _generate_pdf_old(self):
        ctx = self._context.copy()

        runModel = self.env['hr.payslip.run']
        mailModel = self.env['mail.compose.message']
        template = self.env.ref('l10n_mx_payslip.email_template_payroll', raise_if_not_found=False)
        for payslip in self:
            if payslip.l10n_mx_edi_cfdi_uuid and payslip.employee_id.address_home_id.email:
                ctx = {
                    'lang': 'es_MX', 
                    'tz': 'America/Monterrey',
                    'cfdi_code_emp': payslip.employee_id.cfdi_code_emp,
                    'force_email': True,
                    'default_mass_mailing_name': False, 
                    'default_mass_mailing_id': False, 
                    'active_id': payslip.id, 
                    'active_ids': [payslip.id], 
                    'active_model': 'hr.payslip', 
                    'default_composition_mode': 'comment', 
                    'default_model': 'hr.payslip', 
                    'default_res_id': payslip.id, 
                    'default_template_id': template.id, 
                    'custom_layout': 'mail.message_notification_email'
                }
                payslip.with_context(**ctx).message_post_with_template(template.id, email_layout_xmlid="mail.message_notification_email")
                payslip.write({'l10n_mx_edi_sendemail': True})



    def action_payslip_cancel_xml_old(self,reason_cancel=False):
        for payslip in self:
            to_resign = False
            if reason_cancel == '01' and not payslip.l10n_mx_edi_resigned:
                to_resign = True
            if to_resign:
                return self.with_context(reason_cancel=reason_cancel).button_resign_xml()
            else:
                return self.with_context(reason_cancel=reason_cancel).button_cancel_xml()



    def action_payslip_cancel_old(self): #
        ctx = self._context
        edi_result = {}
        cfdi_edi_format = self.env.ref('l10n_mx_edi.edi_cfdi_3_3') # TODO no existe en v17
        for payslip in self:
            if not self.l10n_mx_edi_cfdi_uuid:
                payslip.state = 'cancel'
                continue
            pac_name = payslip.company_id.l10n_mx_edi_pac
            credentials = getattr(cfdi_edi_format, '_l10n_mx_edi_get_%s_credentials_company' % pac_name)(payslip.company_id)            
            if credentials.get('errors'):
                msg = payslip._l10n_mx_edi_format_error_message(_("PAC authentification error:"), credentials['errors'])
                payslip.message_post(body=msg)
                continue
            if payslip.l10n_mx_edi_origin:
                payslip = payslip.with_context(to_cancel_uuid=payslip.l10n_mx_edi_cfdi_uuid_canceled)
            signed_edi = payslip._get_l10n_mx_edi_signed_edi_document()
            if signed_edi:
                cfdi_data = base64.decodebytes(signed_edi.with_context(bin_size=False).datas)            
            res = getattr(cfdi_edi_format, '_l10n_mx_edi_%s_cancel_payslip' % pac_name)(payslip, credentials, cfdi_data)
            if res.get('errors'):
                msg = payslip._l10n_mx_edi_format_error_message(_("PAC failed to cancel the CFDI:"), res['errors'])
                payslip.message_post(body=msg)
                edi_result[payslip.id] = {'error': msg}
                continue

            edi_result[payslip.id] = res
            if res.get('success') == True:
                payslip.write({
                    'state':'cancel'
                })
            # == Chatter ==
            message = _("The CFDI document has been successfully cancelled.")
            payslip.message_post(body=message)
                 


    # -------------------------------------------------------------------------
    # CFDI: PACs
    # -------------------------------------------------------------------------


    def set_l10n_mx_edi_post_time_old(self):
        certificate_date = self.env['l10n_mx_edi.certificate'].sudo().get_mx_current_datetime()
        if not self.invoice_date:
            self.invoice_date = certificate_date.date()
        issued_address = self._get_l10n_mx_edi_issued_address()
        tz = self._l10n_mx_edi_get_cfdi_partner_timezone(issued_address)
        tz_force = self.env['ir.config_parameter'].sudo().get_param('l10n_mx_edi_tz_%s' % self.journal_id.id, default=None)
        if tz_force:
            tz = timezone(tz_force)
        self.l10n_mx_edi_post_time = fields.Datetime.to_string(datetime.now(tz))

    def l10n_mx_edi_get_invoice_cfdi_values_old(self):
        def _format_string_cfdi(text, size=100):
            """Replace from text received the characters that are not found in the
            regex. This regex is taken from SAT documentation
            https://goo.gl/C9sKH6
            text: Text to remove extra characters
            size: Cut the string in size len
            Ex. 'Product ABC (small size)' - 'Product ABC small size'"""
            if not text:
                return None
            text = text.replace('|', ' ')
            return text.strip()[:size]
        def _format_float_cfdi(amount, precision):
            if amount is None or amount is False:
                return None
            return '%.*f' % (precision, amount)
        company = self.company_id
        certificate = company.l10n_mx_edi_certificate_ids.sudo().get_valid_certificate()
        supplier = company.partner_id.commercial_partner_id
        currency_precision = self.currency_id.l10n_mx_edi_decimal_places
        if not self.l10n_mx_edi_post_time:
            self.set_l10n_mx_edi_post_time()
        cfdi_date = datetime.combine(
            fields.Datetime.from_string(self.invoice_date),
            self.l10n_mx_edi_post_time.time(),
        ).strftime('%Y-%m-%dT%H:%M:%S')
        if self.l10n_mx_edi_origin:
            origin_type, origin_uuids = self._l10n_mx_edi_read_cfdi_origin(self.l10n_mx_edi_origin)
        else:
            origin_type = None
            origin_uuids = []
        tz = self.env.user.tz
        fecha_utc =  datetime.now(timezone("UTC"))
        local_date = fecha_utc.astimezone(timezone(tz)).strftime("%Y-%m-%dT%H:%M:%S")
        local_year = int(local_date.split("-")[0])
        cfdi_values = {
            **self._l10n_mx_edi_get_serie_and_folio(),
            **self.l10n_mx_edi_get_common_cfdi_values(),
            'certificate': certificate,
            'certificate_number': certificate.serial_number,
            'certificate_key': certificate.sudo().get_data()[0],
            'record': self,
            'currency_precision': currency_precision,

            'cfdi_date': cfdi_date,
            'format_string': _format_string_cfdi,
            'format_float': _format_float_cfdi,
            'issued_address': self._get_l10n_mx_edi_issued_address(),
            'supplier': supplier,
            'customer': self.employee_id,

            'origin_type': origin_type,
            'origin_uuids': origin_uuids,
            'local_date': local_date,
            'compensacion_saldos_favor': "%s"%(local_year-1),
            'ultimo_sueldo_mensual': self._get_salary_line_total('SD') * 30
        }
        return cfdi_values

    # -------------------------------------------------------------------------
    # SAT
    # -------------------------------------------------------------------------
    def action_l10n_mx_edi_force_generate_cfdi_old(self):
        self.l10n_mx_edi_force_generate_cfdi = True
        self.move_id._update_payments_edi_documents()

    # PDF Report CFDI
    def _action_create_account_move_old(self):
        return True

    # Odooo BASE
    @api.model
    def _cron_generate_pdf_old(self):
        payslips = self.search([
            ('state', 'in', ['done', 'paid']),
            ('queued_for_pdf', '=', True),
        ])
        if not payslips:
            return
        BATCH_SIZE = 50
        payslips_batch = payslips[:BATCH_SIZE]
        payslips_batch._generate_pdf()
        payslips_batch.write({'queued_for_pdf': False})
        # if necessary, retrigger the cron to generate more pdfs
        if len(payslips) > BATCH_SIZE:
            self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()

    @api.model
    def payslip_generate_pdf_old(self):
        attachmentModel = self.env['ir.attachment'].sudo()
        payslipModel = self.env['hr.payslip'].sudo()
        report = self.env.ref('l10n_mx_payslip.hr_payslip_mx')
        for payslip in self:
            pdf_name = 'NOM-%s - %s' % ((payslip.number or '').replace('/',''), payslip.employee_id.display_name)
            attachment_id = attachmentModel.search([
                ('name', '=', '%s.pdf'%pdf_name),
                ('res_model', '=', payslip._name),
                ('res_id', '=', payslip.id)
            ])
            if not attachment_id:
                pdf_content, dummy = report.sudo()._render_qweb_pdf(payslip.id)
                vals = {
                    'name': '%s.pdf'%pdf_name,
                    'type': 'binary',
                    'datas': base64.encodebytes(pdf_content),
                    'res_model': payslip._name,
                    'res_id': payslip.id
                }
                attachmentModel.with_context(encript_pdf=True, cfdi_code_emp=payslip.employee_id.cfdi_code_emp).create(vals)
                self.env.cr.commit()
        return {}
