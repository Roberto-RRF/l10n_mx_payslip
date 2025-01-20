# -*- coding: utf-8 -*-

from odoo import models, fields, api



class DischargeReason(models.Model):
    _name = 'discharge.reason'
    _description = "Discharge Reason"

    name = fields.Char('Discharge Reason', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)

class RejectReason(models.Model):
    _name = 'reject.reason'
    _description = "Reject Reason"

    name = fields.Char('Reason', required=True)
    company_ids = fields.Many2many('res.company', 'res_company_rejectreason_rel', 'reject_id', 'company_id',
        string='Companies', default=lambda self: self.env.company.ids)    
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)

class MotivationEstatus(models.Model):
    _name = 'motivation.estatus'
    _description = "Motivation Estatus"

    name = fields.Char('Motivation Estatus', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)

class MotivationAction(models.Model):
    _name = 'motivation.action'
    _description = "Motivation Action"

    name = fields.Char('Motivation Action', required=True)
    estatus_id = fields.Many2one('motivation.estatus', string="Estatus")
    assistance = fields.Boolean(string="Asistencia")
    payroll = fields.Boolean(string="Ver en Nomina")
    rh = fields.Boolean(string="Ver en RH")
    company_ids = fields.Many2many('res.company', 'res_company_motivationaction_rel', 'action_id', 'company_id',
        string='Companies', default=lambda self: self.env.company.ids)     
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    imss_move = fields.Selection([
            ('R','REINGRESO'),
            ('M','MODIFICACIÓN DE SALARIO'),
            ('1','TERMINO DE CONTRATO'),
            ('2','SEPARACION VOLUNTARIA'),
            ('3','ABANDONO DE EMPLEO'),
            ('4','DEFUNCIÓN'),
            ('5','CLAUSURA'),
            ('6','OTRAS'),
            ('7','AUSENTISMO'),
            ('8','RESCISION DE CONTRATO'),
            ('9','JUBILACION'),
            ('A','PENSION')
        ], string="Movimiento IMSS")

class MotivationReason(models.Model):
    _name = 'motivation.reason'
    _description = "Motivation Reason"

    name = fields.Char('Motivation', required=True)
    action_id = fields.Many2one('motivation.action', string="Action")
    hide_payroll = fields.Boolean('No mostrar en control de movimientos')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)

class MotivationMotivation(models.Model):
    _name = 'motivation.motivation'
    _description = "Motivation Motivation"
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    estatus_id = fields.Many2one('motivation.estatus', string='Motivation Estatus', required=True)
    action_id = fields.Many2one('motivation.action', string='Motivation Action', required=True)
    motivation_id = fields.Many2one('motivation.reason', string='Motivation', required=True)
    effective_date = fields.Date(string="Effective Date", required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)

    state = fields.Selection([
        ('draft','Borrador'),
        ('historic','Histórico'),
        ('pennding','Pendiente'),
        ('ok','Vigente'),
        ('baja','Baja')
    ], string=u"Estado en Nómina")
    send_imss = fields.Selection([
        ('send','Enviar'),
        ('not','No Enviar')
    ], string=u"Enviar IMSS")
    alimony = fields.Boolean(string="Alimony")
    assistance = fields.Boolean(string="Asistencia")
    cfdi_alta_infonavit = fields.Date(string="Alta Infonavit")
    cfdi_code_emp = fields.Char(string="No Empleado", related="employee_id.cfdi_code_emp", store=True)
    currency_id = fields.Many2one('res.currency', related="employee_id.currency_id", store=True)
    company_id = fields.Many2one('res.company', related="employee_id.company_id", store=True)
    cfdi_dto_infonavit = fields.Float(string="Descuento Infonavit")
    cfdi_descuento_infonavit = fields.Char(string="Descuento", compute="_compute_cfdi_descuento_infonavit", store=True)
    @api.depends("cfdi_dto_infonavit")
    def _compute_cfdi_descuento_infonavit(self):
        for rec in self:
            rec.cfdi_descuento_infonavit = '%10.4f' % rec.cfdi_dto_infonavit
    cfdi_infonavit = fields.Char(string="No. Infonavit")
    cfdi_sueldo_infonavit = fields.Float(string="Sueldo Integrado al Infonavit")
    cfdi_sueldo_infonavit = fields.Float(string="Sueldo Integrado al Infonavit")
    cfdi_tipo_dto_infonavit_id = fields.Many2one("l10n_mx_payroll.tipodescuento", string="Tipo de Descuento")
    contract_id = fields.Many2one("hr.contract", string="Contrato")
    daily_wage = fields.Monetary(string="Salario Diario")
    date_dispmag = fields.Date(string="Fecha de envío")
    days = fields.Integer(string="Dias")
    dispmag = fields.Boolean(string="DISPMAG")
    employer_registration = fields.Many2one("l10n_mx_payroll.regpat")
    fijo_pension = fields.Monetary(string="Fijo")
    fire = fields.Boolean(string="Baja de Empleado")
    infonavit = fields.Boolean(string="Con INFONAVIT")
    move_type_infonavit = fields.Selection([
            ('15','[15] Inicio de Crédito de Vivienda (ICV)'),
            ('16','[16] Fecha de Suspensión de Descuento (FS)'),
            ('17','[17] Reinicio de Descuento (RD)'),
            ('18','[18] Modificación de Tipo de Descuento (MTD)'),
            ('19','[19] Modificación de Valor de Descuento (MVD)'),
            ('20','[20] Modificación de Número de Crédito (MND)')
        ], string="Tipo de Movimiento")
    payroll_ok = fields.Boolean(string="OK Nómina")
    payroll_state = fields.Selection([
            ('draft','Borrador'),
            ('historic','Histórico'),
            ('pennding','Pendiente'),
            ('ok','Vigente'),('baja','Baja')
        ], string="Estado en Nómina")
    pension_alimenticia = fields.Selection([
            ('porcentaje1','Porcentaje 1'),
            ('porcentaje2','Porcentaje 2'),
            ('porcentaje3','Porcentaje 3'),
            ('fijo','Importe Fijo')
        ], string="Tipo de pensión")
    porcentaje_pension = fields.Float(string="Porcentaje")
    rh = fields.Boolean(related="action_id.rh", string="Ver por RH")
    factor = fields.Float(string="Factor")
    factor_chr = fields.Char(string="Factor chr", compute="_compute_factor_chr")
    @api.depends("factor")
    def _compute_factor_chr(self):
        for rec in self:
            rec.factor_chr = "%.4f"%rec.factor


    @api.onchange('estatus_id')
    def onchange_estatus_id(self):
        self.action_id = False 
        self.motivation_id = False 
    
    @api.onchange('action_id')
    def onchange_action_id(self):
        self.motivation_id = False

    def button_enviar(self):
        print('asdasd')
