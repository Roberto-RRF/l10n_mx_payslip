# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _

class TipoRegla(models.Model):
    _name = "l10n_mx_payroll.tipo"
    _description = "Tipo de Regla"
    
    name = fields.Char(string="Tipo", required=True)

class TipoHoras(models.Model):
    _name = "l10n_mx_payroll.tipo_horas"
    _description = "Tipo horas"

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string=u"Codigo Catalogo SAT", required=True)

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "[%s] %s" % (rec.code, rec.name or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        recs = super(TipoHoras, self).name_search(name, args=args, operator=operator, limit=limit)
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('code', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

class CodigoAgrupador(models.Model):
    _name = "l10n_mx_payroll.codigo_agrupador"
    _description = "Codigo Agrupador"

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string=u"Codigo Catalogo SAT", required=True)
    cfdi_tipo_id = fields.Many2one("l10n_mx_payroll.tipo", string="Tipo", required=True)

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "[%s] %s" % (rec.code, rec.name or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        recs = super(CodigoAgrupador, self).name_search(name, args=args, operator=operator, limit=limit)
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('code', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

class RegistroPatronal(models.Model):
    _name = 'l10n_mx_payroll.regpat'
    _description = 'Registro Patronal'
    _check_company_auto = True
    
    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", size=64, required=True, default="")
    address_id = fields.Many2one('res.partner', 'Address')
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)    

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "[%s] %s" % (rec.code, rec.name or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        recs = super(RegistroPatronal, self).name_search(name, args=args, operator=operator, limit=limit)
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('code', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
