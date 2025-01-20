# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

CFDITIPO = [
    ('p', 'Percepciones'),
    ('d', 'Deducciones'),
    ('i', 'Incapacidades'),
    ('o', 'Otros Pagos')
]
CFDITIPOPERCEPCION = [
    ('001', '[001] Sueldos, Salarios  Rayas y Jornales'),
    ('002', '[002] Gratificación Anual (Aguinaldo)'),
    ('003', '[003] Participación de los Trabajadores en las Utilidades PTU'),
    ('004', '[004] Reembolso de Gastos Médicos Dentales y Hospitalarios'),
    ('005', '[005] Fondo de Ahorro'),
    ('006', '[006] Caja de ahorro'),
    ('009', '[009] Contribuciones a Cargo del Trabajador Pagadas por el Patrón'),
    ('010', '[010] Premios por puntualidad'),
    ('011', '[011] Prima de Seguro de vida'),
    ('012', '[012] Seguro de Gastos Médicos Mayores'),
    ('013', '[013] Cuotas Sindicales Pagadas por el Patrón'),
    ('014', '[014] Subsidios por incapacidad'),
    ('015', '[015] Becas para trabajadores y/o hijos'),
    ('019', '[019] Horas extra'),
    ('020', '[020] Prima dominical'),
    ('021', '[021] Prima vacacional'),
    ('022', '[022] Prima por antigüedad'),
    ('023', '[023] Pagos por separación'),
    ('024', '[024] Seguro de retiro'),
    ('025', '[025] Indemnizaciones'),
    ('026', '[026] Reembolso por funeral'),
    ('027', '[027] Cuotas de seguridad social pagadas por el patrón'),
    ('028', '[028] Comisiones'),
    ('029', '[029] Vales de despensa'),
    ('030', '[030] Vales de restaurante'),
    ('031', '[031] Vales de gasolina'),
    ('032', '[032] Vales de ropa'),
    ('033', '[033] Ayuda para renta'),
    ('034', '[034] Ayuda para artículos escolares'),
    ('035', '[035] Ayuda para anteojos'),
    ('036', '[036] Ayuda para transporte'),
    ('037', '[037] Ayuda para gastos de funeral'),
    ('038', '[038] Otros ingresos por salarios'),
    ('039', '[039] Jubilaciones, pensiones o haberes de retiro'),
    ('044', '[044] Jubilaciones, pensiones o haberes de retiro en parcialidades'),
    ('045', '[045] Ingresos en acciones o títulos valor que representan bienes'),
    ('046', '[046] Ingresos asimilados a salarios'),
    ('047', '[047] Alimentación diferentes a los establecidos en el Art 94 último párrafo LISR'),
    ('048', '[048] Habitación'),
    ('049', '[049] Premios por asistencia'),
    ('050', '[050] Viáticos'),
    ('051', '[051] Pagos por gratificaciones, primas, compensaciones, recompensas u otros a extrabajadores derivados de jubilación en parcialidades'),
    ('052', '[052] Pagos que se realicen a extrabajadores que obtengan una jubilación en parcialidades derivados de la ejecución de resoluciones judicial o de un laudo'),
    ('053', '[053] Pagos que se realicen a extrabajadores que obtengan una jubilación en una sola exhibición derivados de la ejecución de resoluciones judicial o de un laudo')
]
CFDITIPODEDUCCION = [
    ('001', '[001] Seguridad social'),
    ('002', '[002] ISR'),
    ('003', '[003] Aportaciones a retiro, cesantía en edad avanzada y vejez.'),
    ('004', '[004] Otros'),
    ('005', '[005] Aportaciones a Fondo de vivienda'),
    ('006', '[006] Descuento por incapacidad'),
    ('007', '[007] Pensión alimenticia'),
    ('008', '[008] Renta'),
    ('009', '[009] Préstamos provenientes del Fondo Nacional de la Vivienda para los Trabajadores'),
    ('010', '[010] Pago por crédito de vivienda'),
    ('011', '[011] Pago de abonos INFONACOT'),
    ('012', '[012] Anticipo de salarios'),
    ('013', '[013] Pagos hechos con exceso al trabajador'),
    ('014', '[014] Errores'),
    ('015', '[015] Pérdidas'),
    ('016', '[016] Averías'),
    ('017', '[017] Adquisición de artículos producidos por la empresa o establecimiento'),
    ('018', '[018] Cuotas para la constitución y fomento de sociedades cooperativas y de cajas de ahorro'),
    ('019', '[019] Cuotas sindicales'),
    ('020', '[020] Ausencia (Ausentismo)'),
    ('021', '[021] Cuotas obrero patronales'),
    ('022', '[022] Impuestos Locales'),
    ('023', '[023] Aportaciones voluntarias'),
    ('024', '[024] Ajuste en Gratificación Anual (Aguinaldo) Exento'),
    ('025', '[025] Ajuste en Gratificación Anual (Aguinaldo) Gravado'),
    ('026', '[026] Ajuste en Participación de los Trabajadores en las Utilidades PTU Exento'),
    ('027', '[027] Ajuste en Participación de los Trabajadores en las Utilidades PTU Gravado'),
    ('028', '[028] Ajuste en Reembolso de Gastos Médicos Dentales y Hospitalarios Exento'),
    ('029', '[029] Ajuste en Fondo de ahorro Exento'),
    ('030', '[030] Ajuste en Caja de ahorro Exento'),
    ('031', '[031] Ajuste en Contribuciones a Cargo del Trabajador Pagadas por el Patrón Exento'),
    ('032', '[032] Ajuste en Premios por puntualidad Gravado'),
    ('033', '[033] Ajuste en Prima de Seguro de vida Exento'),
    ('034', '[034] Ajuste en Seguro de Gastos Médicos Mayores Exento'),
    ('035', '[035] Ajuste en Cuotas Sindicales Pagadas por el Patrón Exento'),
    ('036', '[036] Ajuste en Subsidios por incapacidad Exento'),
    ('037', '[037] Ajuste en Becas para trabajadores y/o hijos Exento'),
    ('038', '[038] Ajuste en Horas extra Exento'),
    ('039', '[039] Ajuste en Horas extra Gravado'),
    ('040', '[040] Ajuste en Prima dominical Exento'),
    ('041', '[041] Ajuste en Prima dominical Gravado'),
    ('042', '[042] Ajuste en Prima vacacional Exento'),
    ('043', '[043] Ajuste en Prima vacacional Gravado'),
    ('044', '[044] Ajuste en Prima por antigüedad Exento'),
    ('045', '[045] Ajuste en Prima por antigüedad Gravado'),
    ('046', '[046] Ajuste en Pagos por separación Exento'),
    ('047', '[047] Ajuste en Pagos por separación Gravado'),
    ('048', '[048] Ajuste en Seguro de retiro Exento'),
    ('049', '[049] Ajuste en Indemnizaciones Exento'),
    ('050', '[050] Ajuste en Indemnizaciones Gravado'),
    ('051', '[051] Ajuste en Reembolso por funeral Exento'),
    ('052', '[052] Ajuste en Cuotas de seguridad social pagadas por el patrón Exento'),
    ('053', '[053] Ajuste en Comisiones Gravado'),
    ('054', '[054] Ajuste en Vales de despensa Exento'),
    ('055', '[055] Ajuste en Vales de restaurante Exento'),
    ('056', '[056] Ajuste en Vales de gasolina Exento'),
    ('057', '[057] Ajuste en Vales de ropa Exento'),
    ('058', '[058] Ajuste en Ayuda para renta Exento'),
    ('059', '[059] Ajuste en Ayuda para artículos escolares Exento'),
    ('060', '[060] Ajuste en Ayuda para anteojos Exento'),
    ('061', '[061] Ajuste en Ayuda para transporte Exento'),
    ('062', '[062] Ajuste en Ayuda para gastos de funeral Exento'),
    ('063', '[063] Ajuste en Otros ingresos por salarios Exento'),
    ('064', '[064] Ajuste en Otros ingresos por salarios Gravado'),
    ('065', '[065] Ajuste en Jubilaciones, pensiones o haberes de retiro en una sola exhibición Exento '),
    ('066', '[066] Ajuste en Jubilaciones, pensiones o haberes de retiro en una sola exhibición Gravado'),
    ('067', '[067] Ajuste en Pagos por separación Acumulable'),
    ('068', '[068] Ajuste en Pagos por separación No acumulable'),
    ('069', '[069] Ajuste en Jubilaciones, pensiones o haberes de retiro en parcialidades Exento'),
    ('070', '[070] Ajuste en Jubilaciones, pensiones o haberes de retiro en parcialidades Gravado'),
    ('071', '[071] Ajuste en Subsidio para el empleo (efectivamente entregado al trabajador)'),
    ('072', '[072] Ajuste en Ingresos en acciones o títulos valor que representan bienes Exento'),
    ('073', '[073] Ajuste en Ingresos en acciones o títulos valor que representan bienes Gravado'),
    ('074', '[074] Ajuste en Alimentación Exento'),
    ('075', '[075] Ajuste en Alimentación Gravado'),
    ('076', '[076] Ajuste en Habitación Exento'),
    ('077', '[077] Ajuste en Habitación Gravado'),
    ('078', '[078] Ajuste en Premios por asistencia'),
    ('079', '[079] Ajuste en Pagos distintos a los listados y que no deben considerarse como ingreso por sueldos, salarios o ingresos asimilados.'),
    ('080', '[080] Ajuste en Viáticos gravados'),
    ('081', '[081] Ajuste en Viáticos (entregados al trabajador)'),
    ('082', '[082] Ajuste en Fondo de ahorro Gravado'),
    ('083', '[083] Ajuste en Caja de ahorro Gravado'),
    ('084', '[084] Ajuste en Prima de Seguro de vida Gravado'),
    ('085', '[085] Ajuste en Seguro de Gastos Médicos Mayores Gravado'),
    ('086', '[086] Ajuste en Subsidios por incapacidad Gravado'),
    ('087', '[087] Ajuste en Becas para trabajadores y/o hijos Gravado'),
    ('088', '[088] Ajuste en Seguro de retiro Gravado'),
    ('089', '[089] Ajuste en Vales de despensa Gravado'),
    ('090', '[090] Ajuste en Vales de restaurante Gravado'),
    ('091', '[091] Ajuste en Vales de gasolina Gravado'),
    ('092', '[092] Ajuste en Vales de ropa Gravado'),
    ('093', '[093] Ajuste en Ayuda para renta Gravado'),
    ('094', '[094] Ajuste en Ayuda para artículos escolares Gravado'),
    ('095', '[095] Ajuste en Ayuda para anteojos Gravado'),
    ('096', '[096] Ajuste en Ayuda para transporte Gravado'),
    ('097', '[097] Ajuste en Ayuda para gastos de funeral Gravado'),
    ('098', '[098] Ajuste a ingresos asimilados a salarios gravados'),
    ('099', '[099] Ajuste a ingresos por sueldos y salarios gravados'),
    ('100', '[100] Ajuste en Viáticos exentos'),
    ('101', '[101] ISR Retenido de ejercicio anterior'),
    ('102', '[102] Ajuste a pagos por gratificaciones, primas, compensaciones, recompensas u otros a extrabajadores derivados de jubilación en parcialidades, gravados'),
    ('103', '[103] Ajuste a pagos que se realicen a extrabajadores que obtengan una jubilación en parcialidades derivados de la ejecución de una resolución judicial o de un laudo gravados'),
    ('104', '[104] Ajuste a pagos que se realicen a extrabajadores que obtengan una jubilación en parcialidades derivados de la ejecución de una resolución judicial o de un laudo exentos'),
    ('105', '[105] Ajuste a pagos que se realicen a extrabajadores que obtengan una jubilación en una sola exhibición derivados de la ejecución de una resolución judicial o de un laudo gravados'),
    ('106', '[106] Ajuste a pagos que se realicen a extrabajadores que obtengan una jubilación en una sola exhibición derivados de la ejecución de una resolución judicial o de un laudo exentos'),
    ('107', '[107] Ajuste al Subsidio Causado')
]
CFDITIPOOTROSPAGOS = [
    ('001', '[001] Reintegro de ISR pagado en exceso (siempre que no haya sido enterado al SAT).'),
    ('002', '[002] Subsidio para el empleo (efectivamente entregado al trabajador).'),
    ('003', '[003] Viáticos (entregados al trabajador).'),
    ('004', '[004] Aplicación de saldo a favor por compensación anual.'),
    ('005', '[005] Reintegro de ISR retenido en exceso de ejercicio anterior (siempre que no haya sido enterado al SAT).'),
    ('006', '[006] Alimentos en bienes (Servicios de comedor y comida) Art 94 último párrafo LISR.'),
    ('007', '[007] ISR ajustado por subsidio.'),
    ('008', '[008] Subsidio efectivamente entregado que no correspondía (Aplica sólo cuando haya ajuste al cierre de mes en relación con el Apéndice 7 de la guía de llenado de nómina).'),
    ('009', '[009] Reembolso de descuentos efectuados para el crédito de vivienda.'),
    ('999', '[999] Pagos distintos a los listados y que no deben considerarse como ingreso por sueldos, salarios o ingresos asimilados.')
]
CFDITIPOINCAPACIDAD = [
    ('01', '[01] Riesgo de trabajo.'),
    ('02', '[02] Enfermedad en general.'),
    ('03', '[03] Maternidad.'),
    ('04', '[04] Licencia por cuidados médicos de hijos diagnosticados con cáncer.')
]


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    # ==== CFDI fields Odoo12 ====
    cfdi_tipo_id = fields.Many2one('l10n_mx_payroll.tipo', string=u"Tipo +")
    cfdi_tipohoras_id = fields.Many2one("l10n_mx_payroll.tipo_horas", string="Tipo Horas Extras +")
    cfdi_codigoagrupador_id = fields.Many2one('l10n_mx_payroll.codigo_agrupador', string=u"Código Agrupador +")
    # cfdi_agrupacion_id = fields.Many2one('hr.salary.rule.group', string='Agrupacion +')

    cfdi_tipo_neg_id = fields.Many2one('l10n_mx_payroll.tipo', string=u"Tipo -")
    cfdi_tipohoras_neg_id = fields.Many2one("l10n_mx_payroll.tipo_horas", string="Tipo Horas Extras -")
    cfdi_codigoagrupador_neg_id = fields.Many2one('l10n_mx_payroll.codigo_agrupador', string=u"Código Agrupador -")
    # cfdi_agrupacion_neg_id = fields.Many2one('hr.salary.rule.group', string='Agrupacion -')    

    DEFAULT_PYTHON_CODE = '''
# Available variables:
#----------------------
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days.
# inputs: object containing the computed inputs.

# Note: returned value have to be set in the variable 'result'
result = 0.0
total_exento = 0.0
total_gravado = 0.0
    '''
    amount_python_compute = fields.Text(string='Python Code', default=DEFAULT_PYTHON_CODE,)

    # Positivo
    cfdi_tipo = fields.Selection(CFDITIPO, string="Tipo CFDI")
    cfdi_tipo_percepcion = fields.Selection(CFDITIPOPERCEPCION, string=u"Tipo de percepción")
    cfdi_tipo_deduccion = fields.Selection(CFDITIPODEDUCCION, string=u"Tipo de deducción")
    cfdi_tipo_otrospagos = fields.Selection(CFDITIPOOTROSPAGOS, string=_('Otros Pagos'),)
    cfdi_tipo_incapacidad = fields.Selection(CFDITIPOINCAPACIDAD, string=_('Tipo Incapacidad'))
    cfdi_codigoagrupador = fields.Char(string="Código Agrupador", compute='_compute_cfdi_codigoagrupador')

    # Negativo
    cfdi_tipo_neg = fields.Selection(CFDITIPO, string="Tipo CFDI Neg")
    cfdi_tipo_percepcion_neg = fields.Selection(CFDITIPOPERCEPCION, string=u"Tipo de percepción Neg.")
    cfdi_tipo_deduccion_neg = fields.Selection(CFDITIPODEDUCCION, string=u"Tipo de deducción Neg.")
    cfdi_tipo_otrospagos_neg = fields.Selection(CFDITIPOOTROSPAGOS, string=_('Otros Pagos Neg.'),)
    cfdi_tipo_incapacidad_neg = fields.Selection(CFDITIPOINCAPACIDAD, string=_('Tipo Incapacidad Neg.'))
    cfdi_codigoagrupador_neg = fields.Char(string="Código Agrupador Neg.", compute='_compute_cfdi_codigoagrupador')    

    @api.depends(
        'cfdi_tipo', 
        'cfdi_tipo_percepcion', 
        'cfdi_tipo_deduccion', 
        'cfdi_tipo_incapacidad', 
        'cfdi_tipo_otrospagos',
        'cfdi_tipo_neg',
        'cfdi_tipo_percepcion_neg', 
        'cfdi_tipo_deduccion_neg', 
        'cfdi_tipo_incapacidad_neg', 
        'cfdi_tipo_otrospagos_neg',
    )
    def _compute_cfdi_codigoagrupador(self):
        for rec in self:
            codigoagrupador, codigoagrupador_neg = '', ''
            if rec.cfdi_tipo or rec.cfdi_tipo_neg:
                tipoPos = {
                    'p': rec.cfdi_tipo_percepcion, 'd': rec.cfdi_tipo_deduccion, 'o': rec.cfdi_tipo_otrospagos, 'i': rec.cfdi_tipo_incapacidad 
                }
                codigoagrupador = tipoPos.get( rec.cfdi_tipo ) or ''
                tipoNeg = {
                    'p': rec.cfdi_tipo_percepcion_neg, 'd': rec.cfdi_tipo_deduccion_neg, '0': rec.cfdi_tipo_otrospagos_neg, 'i': rec.cfdi_tipo_incapacidad_neg 
                }
                codigoagrupador_neg = tipoNeg.get( rec.cfdi_tipo_neg ) or ''                
            rec.update({
                'cfdi_codigoagrupador': codigoagrupador,
                'cfdi_codigoagrupador_neg': codigoagrupador_neg
            })

    def _compute_rule(self, localdict):
        """
        :param localdict: dictionary containing the current computation environment
        :return: returns a tuple (amount, qty, rate)
        :rtype: (float, float, float)
        """
        self.ensure_one()
        context = dict(self.env.context)
        amount, qty, rate = super(HrSalaryRule, self)._compute_rule(localdict)
        cfdi_nomina = {
            'total_gravado': localdict.get("total_gravado"), 
            'total_exento': localdict.get("total_exento"), 
            'dias_incapacidad': localdict.get("dias_incapacidad")
        }
        context.setdefault('cfdi_nomina', {})[self.id] = cfdi_nomina
        self.env.context = context
        return amount, qty, rate
        

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    total_exento = fields.Float(string='Total Exento', digits='Payroll' )
    total_gravado = fields.Float(string='Total Gravado', digits='Payroll' )
    dias_incapacidad = fields.Integer(string='Dias Incapacidad')

    cfdi_importe_exento = fields.Float(string='Importe Exento', digits='Payroll' )
    cfdi_importe_gravado = fields.Float(string='Importe Gravado', digits='Payroll' )
    cfdi_tipo = fields.Selection(CFDITIPO, string="Tipo CFDI", store=True)
    cfdi_codigoagrupador = fields.Char(string="Código Agrupador", store=True)
    cfdi_tipo_percepcion = fields.Selection(CFDITIPOPERCEPCION, string=u"Tipo de percepción", store=True)
    cfdi_tipo_deduccion = fields.Selection(CFDITIPODEDUCCION, string=u"Tipo de deducción", store=True)
    cfdi_tipo_otrospagos = fields.Selection(CFDITIPOOTROSPAGOS, string=_('Otros Pagos'), store=True)
    cfdi_tipo_incapacidad = fields.Selection(CFDITIPOINCAPACIDAD, string=_('Tipo Incapacidad'), store=True)


class HrPayrollEditPayslipLine(models.TransientModel):
    _inherit = 'hr.payroll.edit.payslip.line' 

    total_exento = fields.Float(string='Total Exento', digits='Payroll' )
    total_gravado = fields.Float(string='Total Gravado', digits='Payroll' )
    dias_incapacidad = fields.Integer(string='Dias Incapacidad')
    cfdi_importe_exento = fields.Float(string='Importe Exento', digits='Payroll' )
    total_gravado = fields.Float(string='Importe Gravado', digits='Payroll' )
    cfdi_tipo = fields.Selection(CFDITIPO, string="Tipo CFDI", store=True)
    cfdi_codigoagrupador = fields.Char(string="Código Agrupador", store=True)
    cfdi_tipo_percepcion = fields.Selection(CFDITIPOPERCEPCION, string=u"Tipo de percepción", store=True)
    cfdi_tipo_deduccion = fields.Selection(CFDITIPODEDUCCION, string=u"Tipo de deducción", store=True)
    cfdi_tipo_otrospagos = fields.Selection(CFDITIPOOTROSPAGOS, string=_('Otros Pagos'), store=True)
    cfdi_tipo_incapacidad = fields.Selection(CFDITIPOINCAPACIDAD, string=_('Tipo Incapacidad'), store=True)

    def _export_to_payslip_line(self):
        return [{
            'sequence': line.sequence,
            'code': line.code,
            'name': line.name,
            'note': line.note,
            'salary_rule_id': line.salary_rule_id.id,
            'contract_id': line.contract_id.id,
            'employee_id': line.employee_id.id,
            'amount': line.amount,
            'quantity': line.quantity,
            'rate': line.rate,
            'slip_id': line.slip_id.id,
            'total_exento': line.total_exento,
            'total_gravado': line.total_gravado,
            'dias_incapacidad': line.dias_incapacidad,
            'cfdi_tipo': line.cfdi_tipo,
            'cfdi_codigoagrupador': line.cfdi_codigoagrupador,
            'cfdi_tipo_percepcion': line.cfdi_tipo_percepcion,
            'cfdi_tipo_deduccion': line.cfdi_tipo_deduccion,
            'cfdi_tipo_otrospagos': line.cfdi_tipo_otrospagos,
            'cfdi_tipo_incapacidad': line.cfdi_tipo_incapacidad
        } for line in self]
