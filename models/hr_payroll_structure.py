# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _

class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'
    _description = 'Salary Structure'

    @api.model
    def _get_default_rule_ids(self):
        lines_tmp = [
            (0, 0, {
                'name': _('Basic Salary'),
                'sequence': 1,
                'code': 'BASIC',
                'category_id': self.env.ref('hr_payroll.BASIC').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = payslip.paid_amount',
            }),
            (0, 0, {
                'name': _('Gross'),
                'sequence': 100,
                'code': 'GROSS',
                'category_id': self.env.ref('hr_payroll.GROSS').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = categories.BASIC + categories.ALW',
            }),
            (0, 0, {
                'name': _('Net Salary'),
                'sequence': 200,
                'code': 'NET',
                'category_id': self.env.ref('hr_payroll.NET').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = categories.BASIC + categories.ALW + categories.DED',
            }),        
            (0, 0, {
                'name': _('Salario Base Cot Apor'),
                'sequence': 300,
                'code': 'C510D',
                'category_id': self.env.ref('l10n_mx_payslip.ESTADISTICO').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = 0.0',
            }),
            (0, 0, {
                'name': _('Salario Diario Integrado'),
                'sequence': 301,
                'code': 'SD',
                'category_id': self.env.ref('l10n_mx_payslip.ESTADISTICO').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = 0.0',
            }),
            (0, 0, {
                'name': _('Num Dias Pagados'),
                'sequence': 302,
                'code': 'C9',
                'category_id': self.env.ref('l10n_mx_payslip.ESTADISTICO').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = 0.0',
            }),
            (0, 0, {
                'name': _('Otro Pago'),
                'sequence': 303,
                'code': 'C002',
                'category_id': self.env.ref('l10n_mx_payslip.ESTADISTICO').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = 0.0',
                'cfdi_tipo': 'p',
                'cfdi_tipo_otrospagos': '002'
            }), 
        ]
        return lines_tmp

    rule_ids = fields.One2many(
        'hr.salary.rule', 'struct_id',
        string='Salary Rules', default=_get_default_rule_ids)
    l10n_mx_edi_tiponominaespecial = fields.Selection([
        ('ord', 'Nomina Ordinaria'),
        ('ext_nom', 'Nomina Extraordinaria'),
        ('ext_agui', 'Extraordinaria Aguinaldo'),
        ('ext_fini', 'Extraordinaria Finiquito'),
        ('ext_ptu', 'Extraordinaria PTU'),],
    string="Tipo Nomina Especial", default="ord")
