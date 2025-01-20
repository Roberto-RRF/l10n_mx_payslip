# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def _default_employee_code(self):
        if self.id:
            self.cfdi_code_emp = '%.*f' % (6, self.id)

    cfdi_nombre = fields.Char(string='Nombre')
    cfdi_appat = fields.Char(string='Apellido Paterno')
    cfdi_apmat = fields.Char(string='Apellido Materno')
    cfdi_code_emp = fields.Char(string="Codigo de Empleado", index=True, default=_default_employee_code)

    # CFDI
    cfdi_retiroparcialidad = fields.Float(
        string='Monto Diario Parcialidad',
        help=u"Monto diario percibido por el trabajador por jubilación, pensión o retiro cuando el pago es en parcialidades"
    )
    registropatronal_id = fields.Many2one('l10n_mx_payroll.regpat', string='Registro Patronal 01')
    cfdi_registropatronal_id = fields.Many2one('l10n_mx_payroll.regpat', string='Registro Patronal')
    cfdi_curp = fields.Char(string="CURP", size=18, default="")
    cfdi_rfc = fields.Char(string="RFC", size=13, default="")    
    cfdi_numseguridadsocial = fields.Char(string="No. IMSS", size=64, default="")
    cfdi_date_alta = fields.Date(string="Fecha de Alta.")
    cfdi_date_start = fields.Date(string="Date Start")
    cfdi_date_end = fields.Date(string="Date End")
    cfdi_date_contract = fields.Date(string="Contract Date")
    cfdi_anhos_servicio = fields.Float(u"Años de servicio", compute="_onchange_cfdi_anhos_servicio")
    fecha_fondo_de_ahorro = fields.Date(string="Fecha Inicio Fondo de Ahorro.")
    bono_antiguedad = fields.Boolean(string=u"Bono de Antigüedad.")

    def _onchange_cfdi_anhos_servicio(self):
        for emp in self:
            cfdi_date_start = emp.cfdi_date_contract or fields.Date.today()
            cfdi_date_end = emp.cfdi_date_end or fields.Date.today()
            emp.cfdi_anhos_servicio = (cfdi_date_end - cfdi_date_start).days / 365

    cfdi_tipojornada = fields.Selection([
        ('01', '[01] Diurna'),
        ('02', '[02] Nocturna'),
        ('03', '[03] Mixta'),
        ('04', '[04] Por hora'),
        ('05', '[05] Reducida'),
        ('06', '[06] Continuada'),
        ('07', '[07] Partida'),
        ('08', '[08] Por turnos'),
        ('99', '[99] Otra Jornada')
    ], string="Tipo Jornada")
    
    _sql_constraints = [
        ('cfdi_code_emp_uniq', 'unique (cfdi_code_emp)', "Error! Ya hay un empleado con ese codigo."),
    ]

    @api.onchange('cfdi_nombre', 'cfdi_appat', 'cfdi_apmat')
    def _onchange_name(self):
        self.name = '%s %s %s'%( self.cfdi_nombre or '', self.cfdi_appat or '', self.cfdi_apmat or ''  )

    def name_get(self):
        result = []
        for emp in self:
            name = "%s %s %s"%(emp.sudo().cfdi_nombre or '', emp.sudo().cfdi_appat or '', emp.sudo().cfdi_apmat or '')
            result.append((emp.sudo().id, name))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = '%s %s %s'%( vals.get('cfdi_nombre', ''), vals.get('cfdi_appat', ''), vals.get('cfdi_apmat', '') )
            employee = super(HrEmployee, self).create(vals)
            return employee
            
    # Botones de Accion
    def button_altacambio_empleado(self):
        ctx = self.env.context
        button_context = self.get_button_default_context(open_view=1, button='move')
        action = {
            'name': button_context.get('default_name', ''), 
            'type': 'ir.actions.act_window', 
            'res_model': 'hr.emplyee.move.wiz', 
            'view_mode': 'form', 
            'target': 'new',
            'context': button_context,
        }
        return action

    def button_baja_empleado(self):
        ctx = self.env.context
        button_context = self.get_button_default_context(open_view=1, button='fire')
        action = {
            'name': button_context.get('default_name', ''),  
            'type': 'ir.actions.act_window', 
            'res_model': 'hr.emplyee.move.wiz', 
            'view_mode': 'form', 
            'target': 'new',
            'context': button_context,
        }
        return action

    def button_alimony(self):
        ctx = self.env.context
        button_context = self.get_button_default_context(open_view=1, button='alimony')
        action = {
            'name': button_context.get('default_name', ''),  
            'type': 'ir.actions.act_window', 
            'res_model': 'hr.emplyee.move.wiz', 
            'view_mode': 'form', 
            'target': 'new',
            'context': button_context,
        }
        return action

    def button_infonavit(self):
        ctx = self.env.context
        button_context = self.get_button_default_context(open_view=1, button='infonavit')
        infonavit_id = self.env['hr.employee.infonavit'].search([('employee_id', '=', self.id)], order="infonavit_date DESC", limit=1)
        button_context.update({
            'default_infonavit': infonavit_id and infonavit_id.infonavit or '',
            'default_infonavit_discount': infonavit_id and infonavit_id.infonavit_discount or 0.0,
            'default_infonavit_discount_type': infonavit_id.infonavit_discount_type,
            'default_infonavit_move_type': infonavit_id.infonavit_move_type,
        })
        action = {
            'name': button_context.get('default_name', ''),
            'type': 'ir.actions.act_window', 
            'res_model': 'hr.emplyee.move.wiz', 
            'view_mode': 'form', 
            'target': 'new',
            'context': button_context,
        }
        return action
