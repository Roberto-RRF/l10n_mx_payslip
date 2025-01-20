# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

#class HrJob(models.Model):
#    _inherit = 'hr.job'
#    tab_id = fields.Many2one('hr.salary.tab', string='Salary Tab',  company_dependent=True, tracking=True)
#    code = fields.Char (string="Code", compute="_compute_code_level_scale")
#    level_id = fields.Many2one('hr.salary.tab.level', string="Level", compute="_compute_code_level_scale")
#    scale_id = fields.Many2one('hr.salary.tab.level', string="Scale", compute="_compute_code_level_scale")
#    reference = fields.Char (string="Internal Reference", tracking=True)
#    @api.depends('tab_id') 
#    def _compute_code_level_scale(self):
#        for job in self:
#            job.code = job.tab_id.codeLevel
#            job.level_id = job.tab_id.level_id.id
#            job.scale_id = job.tab_id.scale_id.id

class ResCompanyRegistration(models.Model):
    _name = 'res.company.registration'
    _description = "Employer Registration"
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Name', required=True, index=True)
    company_id = fields.Many2one('res.company', required=True)
    registration = fields.Char(string='Employer Registration')
    address_id = fields.Many2one('res.partner', string='Address')

class HrEmployeeMoveType(models.Model):
    _name = 'hr.employee.move.type'
    _description = "Employee Move Type"
    _order = 'ttype, name'

    name = fields.Char(string='Name', required=True, index=True, translate=True)
    ttype = fields.Selection([
        ('status', 'Status'),
        ('action', 'Action'),
        ('reason', 'Reason'),
        ('imss','IMSS')
    ], groups="hr.group_hr_user")
    company_ids = fields.Many2many(
        'res.company', 'move_company_rel',
        'move_id', 'company_id', groups="hr.group_hr_manager",
        string='Companies')
    status_id = fields.Many2one('hr.employee.move.type', 'Status', domain=[('ttype','=','status')])
    action_id = fields.Many2one('hr.employee.move.type', 'Action', domain=[('ttype','=','action')])
    imss_move = fields.Many2one('hr.employee.move.type', 'IMSS Move', domain=[('ttype','=','imss')])
    code_imss = fields.Char(string='Code IMSS')
    code_sua = fields.Char(string='Code SUA')
    move_control = fields.Boolean('Move Control')


class HrEmployeeCommon(models.Model):
    _name = 'hr.employee.common'
    _description = "Employee Common"
    _order = 'effective_date DESC'

    # COMMON
    name = fields.Char('Registration Number of the Employee', groups="hr.group_hr_user", copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employees', groups='base.group_user', copy=False, required=True)
    employer_registration = fields.Many2one('res.company.registration', string='Employer Registration')
    workplace_id = fields.Many2one('res.partner', string='Workplace')
    company_id = fields.Many2one('res.company',required=True)
    currency_id = fields.Many2one('res.currency', required=True, string='Currency', default=lambda self: self.env.company.currency_id)
    effective_date = fields.Date('Efective Date')
    state = fields.Selection([
        ('draft','Draft'),
        ('historic','Historic'),
        ('pennding','Pennding'),
        ('current','Current'),
        ('dismissed','Dismissed')
    ], 'State')

class HrEmployeeWage(models.Model):
    _name = 'hr.employee.wage'
    _inherit = 'hr.employee.common'
    _description = "Employee Wage"

    # WAGE = COMMON + WAGE
    daily_wage = fields.Monetary(string='Daily Wage', default=0.0, currency_field='currency_id')
    monthly_wage = fields.Monetary(string='Monthly Wage', default=0.0, currency_field='currency_id', 
        compute='_compute_monthly_wage', store=True)
    variable_wage = fields.Monetary(string='Variable Wage', default=0.0, currency_field='currency_id')
    factor = fields.Float(string='Factor', digits=(5,4))
    sdi = fields.Monetary(string='SDI', default=0.0, currency_field='currency_id')
    tab_id = fields.Many2one('hr.salary.tab', string='Wage Tab')
    current_tab_id = fields.Many2one('hr.salary.tab', string='Current Wage Tab')
    category_ids = fields.Many2many('hr.employee.category',
        'employee_wage_category_rel', 'wage_id', 'category_id', string='Tags')

    @api.depends('daily_wage')
    def _compute_monthly_wage(self):
        for move in self:
            move.monthly_wage = move.daily_wage * 30 # TODO make it configurable

class HrEmployeeMove(models.Model):
    _name = 'hr.employee.move'
    _inherit = 'hr.employee.wage'
    _description = "Employee Move"

    # EMPLOYEE MOVE = COMMON + WAGE + EMPLOYEE MOVE
    status_id = fields.Many2one('hr.employee.move.type', 'Status', domain=[('ttype','=','status')])
    action_id = fields.Many2one('hr.employee.move.type', 'Action', domain=[('ttype','=','action')])
    reason_id = fields.Many2one('hr.employee.move.type', 'Reason', domain=[('ttype','=','reason')])
    send_imss = fields.Selection([('send','Send'),('not','Not Send')], 'Send IMSS')
    date_send_imss = fields.Datetime('Date Send IMSS')
    dispmag = fields.Boolean('DISPMAG')
    date_dispmag = fields.Date('Send DISPMAG')
    category_ids = fields.Many2many('hr.employee.category',
        'employee_move_category_rel', 'move_id', 'category_id', string='Tags')

class HrEmployeeAlimony(models.Model):
    _name = 'hr.employee.alimony'
    _inherit = 'hr.employee.common'
    _description = "Employee Alimony"

    # ALIMONY = COMMON + ALIMONY
    alimony_amount = fields.Monetary(string='Alimony Amount', default=0.0, currency_field='currency_id')
    alimony_type = fields.Selection([
            ('percentage1','Porcentage 1'),
            ('percentage2','Porcentage 2'),
            ('percentage3','Porcentage 3'),
            ('fixed','Fixed Amount')
        ], 'Alimony Type')

class HrEmployeeInfonavit(models.Model):
    _name = 'hr.employee.infonavit'
    _inherit = 'hr.employee.common'
    _description = "Employee Infonavit"

    # INFONAVIT = COMMON + INFONAVIT
    infonavit = fields.Char('No. INFONAVIT', copy=False)
    infonavit_date = fields.Date('INFONAVIT Discharge Date', copy=False)
    infonavit_discount = fields.Float(string='INFONAVIT Discount', digits=(5,4))
    infonavit_sdi = fields.Monetary(string='SDI INFONAVIT', currency_field='currency_id')
    infonavit_discount_type = fields.Selection([
            ('1','[1] Porcentage'),
            ('2','[2] Monetary Fixed Amount'),
            ('3','[3] VSM DF Fixed Amount'),
            ('4','[4] Suspension Discount')
        ], 'INFONAVIT Discount Type')
    infonavit_move_type = fields.Selection([
            ('15','[15] Home Credit Start (ICV)'),
            ('16','[16] Discount Suspension Date (FS)'),
            ('17','[17] Discount Restart (RD)'),
            ('18','[18] Discount Type Modification (MTD)'),
            ('19','[19] Discount Value Modification (MVD)'),
            ('20','[20] Credit Number Modification (MND)')
        ], 'INFONAVIT Move Type')

# hr_department_rules



