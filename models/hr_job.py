# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _

class ClaseRiesgo(models.Model):
    _name = "l10n_mx_payroll.riesgo_puesto"
    _description = "Clase Riesgo"
    
    name = fields.Char(string="Descripcion", required=True)
    code = fields.Char(string=u"Codigo Catalogo SAT", required=True)

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "[%s] %s" % (rec.code, rec.name or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        recs = super(ClaseRiesgo, self).name_search(name, args=args, operator=operator, limit=limit)
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('code', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

class HrJob(models.Model):
    _inherit = 'hr.job'

    cfdi_riesgopuesto_id = fields.Many2one("l10n_mx_payroll.riesgo_puesto", string="Clase riesgo")
    cfdi_riesgopuesto = fields.Selection([
        ('1', '[1] Clase I'),
        ('2', '[2] Clase II'),
        ('3', '[3] Clase III'),
        ('4', '[4] Clase IV'),
        ('5', '[5] Clase V'),
        ('99', '[99] No aplica')
    ], string="Riesgo Puesto")
