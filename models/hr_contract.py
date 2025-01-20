# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields, models, _

class HrContract(models.Model):
    _inherit = 'hr.contract'

    cfdi_tipocontrato = fields.Selection([
        ('01', '[01] Contrato de trabajo por tiempo indeterminado'),
        ('02', '[02] Contrato de trabajo para obra determinada'),
        ('03', '[03] Contrato de trabajo por tiempo determinado'),
        ('04', '[04] Contrato de trabajo por temporada'),
        ('05', '[05] Contrato de trabajo sujeto a prueba'),
        ('06', '[06] Contrato de trabajo con capacitación inicial'),
        ('07', '[07] Modalidad de contratación por pago de hora laborada'),
        ('08', '[08] Modalidad de trabajo por comisión laboral'),
        ('09', '[09] Modalidades de contratación donde no existe relación de trabajo'),
        ('10', '[10] Jubilación, pensión, retiro.'),
        ('99', '[99] Otro contrato'),
    ], string="Tipo Contrato", default='01')
    cfdi_tiporegimen = fields.Selection([
        ('02', '[02] Sueldos'),
        ('03', '[03] Jubilados'),
        ('04', '[04] Pensionados'),
        ('05', '[05] Asimilados Miembros Sociedades Cooperativas Produccion'),
        ('06', '[06] Asimilados Integrantes Sociedades Asociaciones Civiles'),
        ('07', '[07] Asimilados Miembros consejos'),
        ('08', '[08] Asimilados comisionistas'),
        ('09', '[09] Asimilados Honorarios'),
        ('10', '[10] Asimilados acciones'),
        ('11', '[11] Asimilados otros'),
        ('12', '[12] Jubilados o Pensionados'),
        ('13', '[13] Indemnización o Separación'),
        ('99', '[99] Otro Regimen')
    ], string="Tipo Regimen")
    cfdi_periodicidadpago = fields.Selection([
        ('01', '[01] Diario'),
        ('02', '[02] Semanal'),
        ('03', '[03] Catorcenal'),
        ('04', '[04] Quincenal'),
        ('05', '[05] Mensual'),
        ('06', '[06] Bimestral'),
        ('07', '[07] Unidad obra'),
        ('08', '[08] Comisión'),
        ('09', '[09] Precio alzado'),
        ('10', '[10] Decenal'),
        ('99', '[99] Otra Periodicidad')
    ], string="Periodicidad Pagos")
    cfdi_sindicalizado = fields.Boolean(string="Sindicalizado", default=False)
