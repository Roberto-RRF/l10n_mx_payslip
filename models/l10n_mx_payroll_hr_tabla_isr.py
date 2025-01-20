# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TablaPrimaRiesgo(models.Model):
    _name = "l10n_mx_payroll.hr_tabla_primariesgo"
    _description = "Tabla Prima Riesgo"
    _rec_name = "fecha"
    _order = 'fecha desc'
    _check_company_auto = True

    fecha = fields.Date(string='Fecha', required=True, index=True, copy=False)
    prima = fields.Float(string="Prima Riesgo", required=True, digits='Payroll Table')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

class TablaCesantiaVejez(models.Model):
    _name = "l10n_mx_payroll.hr_tabla_cesantia"
    _description = "Tabla Cesantia y Vejez"

    cuota_fija = fields.Float(string="Cuota fija", required=False)

    name = fields.Char(string=u"Salario Base", required=False)
    limite_inferior = fields.Float(string=u"Limite inferior", required=True)
    limite_superior = fields.Float(string=u"Limite superior", required=True)
    tasa = fields.Float(string="Couta Patronal (%)", required=True, digits='Payroll Table Percent')

class TablaIsr(models.Model):
    _name = "l10n_mx_payroll.hr_tabla_isr"
    _description = "Tabla ISR"
    
    name = fields.Char(string=u"Año", required=True)
    limite_inferior = fields.Float(string=u"Limite Inferior", required=True)
    limite_superior = fields.Float(string=u"Limite Superior", required=True)
    cuota_fija = fields.Float(string="Cuota Fija", required=True)
    tasa = fields.Float(string="Tasa (%)", required=True)
    periodicidad = fields.Selection([('s','Semanal'), ('d','Decenal'), ('m','Mensual'),('q','Qincena'),('a','Anual')], string="Periodicidad", default='m')

    @api.model
    def calcular_isr(self, ingreso, name):
        tabla_id = self.search([('name', '=', name)], order='limite_inferior asc')
        if not tabla_id:
            raise UserError("Error \n\nNo hay tabla de ISR definida para el año %s"%name)
        rows = self.browse(tabla_id)
        r = rows[0]
        for row in rows:
            if row.limite_superior < 0:
                row.limite_superior = float("inf")
            if row.limite_inferior <= ingreso <= row.limite_superior:
                break
            r = row
        base = ingreso - r.limite_inferior
        isr_sin_subsidio = base * (r.tasa / 100.0) + r.cuota_fija
        
        tabla_s_obj = self.env['l10n_mx_payroll.hr_tabla_subsidio']
        tabla_id = tabla_s_obj.search([('name', '=', name)], order='limite_inferior asc')
        if not tabla_id:
            raise UserError("Error \n\nNo hay tabla de subsidio al empleo definida para el año %s"%name)
        rows = tabla_s_obj.browse(tabla_id)
        r = rows[0]
        for row in rows:
            if row.limite_superior < 0:
                row.limite_superior = float("inf")
            if row.limite_inferior <= ingreso <= row.limite_superior:
                break
            r = row
        isr = isr_sin_subsidio - r.subsidio
        return ingreso - isr
