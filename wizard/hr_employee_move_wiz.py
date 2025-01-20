# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import datetime

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class HrEmployeeMoveWiz(models.TransientModel):
    _name = 'hr.emplyee.move.wiz'
    _description = "Employee Move"

    name = fields.Char(string='Name')
    parameter = fields.Char(string='Parameter')
    employee_id = fields.Many2one('hr.employee', 'Appraisal Employee')
    effective_date = fields.Date('Efective Date', default=lambda self: fields.Date.today())
    tab_id = fields.Many2one('hr.salary.tab', string='Wage Tab')
    daily_wage = fields.Monetary(string='Daily Wage', default=0.0, currency_field='currency_id')

    alimony_amount = fields.Monetary(string='Alimony Amount', default=0.0, currency_field='currency_id')
    alimony_type = fields.Selection([
        ('percentage1','Porcentage 1'),
        ('percentage2','Porcentage 2'),
        ('percentage3','Porcentage 3'),
        ('fixed','Fixed Amount')
    ], 'Alimony Type')

    status_id = fields.Many2one('hr.employee.move.type', 'Status', domain=[('ttype','=','status')])
    action_id = fields.Many2one('hr.employee.move.type', 'Action', domain=[('ttype','=','action')])
    reason_id = fields.Many2one('hr.employee.move.type', 'Reason', domain=[('ttype','=','reason')])
    imss_move = fields.Many2one('hr.employee.move.type', 'IMSS Move', domain=[('ttype','=','imss')])
    currency_id = fields.Many2one('res.currency', string="Currency", required= True, default=lambda self: self.env.company.currency_id)

    infonavit = fields.Char('No. INFONAVIT', copy=False)
    sueldo_infonavit = fields.Float(string='Sueldo Integrado al Infonavit')
    infonavit_discount = fields.Float(string='Discount', digits=(5,4))
    infonavit_discount_type = fields.Selection([
            ('1','[1] Porcentage'),
            ('2','[2] Monetary Fixed Amount'),
            ('3','[3] VSM DF Fixed Amount'),
            ('4','[4] Suspension Discount')
        ], 'Discount Type', default='1')
    infonavit_move_type = fields.Selection([
            ('15','[15] Home Credit Start (ICV)'),
            ('16','[16] Discount Suspension Date (FS)'),
            ('17','[17] Discount Restart (RD)'),
            ('18','[18] Discount Type Modification (MTD)'),
            ('19','[19] Discount Value Modification (MVD)'),
            ('20','[20] Credit Number Modification (MND)')
        ], 'Move Type', default='15')

    def procesar_cambio(self):
        self.ensure_one()
        wageModel = self.env['hr.employee.wage'].sudo()
        emp_val = {
            'active': True,
            'cfdi_date_end': False
        }
        UMA, FACTOR, VARIMSS, SDI, SD = self.process_rules(self.employee_id.id, sd=self.daily_wage, date=self.effective_date, debug=False, move=True)
        wage_val = {
            'employee_id':self.employee_id.id,
            'current_tab_id': self.tab_id.id,
            'effective_date': self.effective_date,
            'daily_wage': self.daily_wage,
            'company_id': self.employee_id.company_id.id,
            'category_ids': [(6,0, self.employee_id.category_ids.ids)],
            'state':'current',
            'factor': FACTOR,
            'variable_wage': VARIMSS,
        }
        reg_wage = wageModel.search([('employee_id', '=', self.employee_id.id), ('state','=','current')])
        if reg_wage.daily_wage != self.daily_wage:
            reg_wage.write({'state':'historic'})
            reg_wage = wageModel.create(wage_val)
        self.employee_id.write(emp_val)
        vals = {
            'name': self.employee_id.cfdi_code_emp,
            'employee_id': self.employee_id.id,
            'current_tab_id': self.tab_id.id,
            'effective_date': self.effective_date,
            'daily_wage': self.daily_wage,
            'company_id': self.employee_id.company_id.id,
            'category_ids': [(6,0, self.employee_id.category_ids.ids)],
            'state':'current',
            'factor': FACTOR,
            'variable_wage': VARIMSS,

            'status_id': self.status_id and self.status_id.id or False,
            'action_id': self.action_id and self.action_id.id or False,
            'reason_id': self.reason_id and self.reason_id.id or False,
            'send_imss': False,
            'date_send_imss': False,
            'dispmag': False,
            'date_dispmag': False,
            'category_ids': [(6,0, self.employee_id.category_ids.ids)],
        }
        self.env['hr.employee.move'].create(vals)
        return {'return':True, 'type':'ir.actions.act_window_close' }

    def procesar_baja(self):
        self.ensure_one()
        wageModel = self.env['hr.employee.wage'].sudo()
        contractModel = self.env['hr.contract']
        self.employee_id.write({
            'active': False,
            'cfdi_date_end': self.effective_date,
            'position_state': 'vacancy'
        })
        self.employee_id.department_position_id.write({
            'position_state': 'vacancy'
        })
        contract = contractModel.search([('employee_id','=',self.employee_id.id),('state','=','open')], limit=1)
        contract.write({'state':'pending'})
        wage_id = wageModel.search([('employee_id','=',self.employee_id.id),('state','=','current')])
        vals = {
            'name': self.employee_id.cfdi_code_emp,
            'employee_id': self.employee_id.id,
            'current_tab_id': self.tab_id and self.tab_id.id,
            'effective_date': self.effective_date,
            'daily_wage': self.daily_wage,
            'company_id': self.employee_id.company_id.id,
            'category_ids': [(6,0, self.employee_id.category_ids.ids)],
            'state':'pennding',

            'status_id': self.status_id and self.status_id.id or False,
            'action_id': self.action_id and self.action_id.id or False,
            'reason_id': self.reason_id and self.reason_id.id or False,
            'send_imss': False,
            'date_send_imss': False,
            'dispmag': False,
            'date_dispmag': False,
            'category_ids': [(6,0, self.employee_id.category_ids.ids)],
        }
        self.env['hr.employee.move'].create(vals)
        return {'return':True, 'type':'ir.actions.act_window_close' }

    def procesar_alimony(self):
        self.ensure_one()
        vals = {
            'name': self.employee_id.cfdi_code_emp,
            'employee_id': self.employee_id.id,
            'effective_date': self.effective_date,
            'company_id': self.employee_id.company_id.id,
            'state':'current',
            'alimony_amount': self.alimony_amount,
            'alimony_type': self.alimony_type,
        }
        self.env['hr.employee.alimony'].create(vals)
        return {'return':True, 'type':'ir.actions.act_window_close' }

    def procesar_infonavit(self):
        self.ensure_one()
        infonavit_id = self.env['hr.employee.infonavit'].search([('employee_id', '=', self.employee_id.id)], order="infonavit_date DESC", limit=1)
        change = (infonavit_id.infonavit == self.infonavit and  \
        infonavit_id.infonavit_date == self.effective_date and  \
        infonavit_id.infonavit_discount == self.infonavit_discount and  \
        infonavit_id.infonavit_discount_type == self.infonavit_discount_type)
        if change:
            vals = {
                'name': self.employee_id.cfdi_code_emp,
                'employee_id': self.employee_id.id,
                'company_id': self.employee_id.company_id.id,
                'effective_date': self.effective_date,
                'state':'current',
                'infonavit': self.infonavit,
                'infonavit_date': self.effective_date,
                'infonavit_discount': self.infonavit_discount,
                'infonavit_discount_type': self.infonavit_discount_type,
                'infonavit_move_type': self.infonavit_move_type,
            }
            self.env['hr.employee.infonavit'].create(vals)
        return {'return':True, 'type':'ir.actions.act_window_close' }


    def get_varimss(self, emp_id, bimestre, debug=False):
        # Variable IMSS VARIMSS_FORM
        today = datetime.datetime.today() #.date()
        CODES = [
            'C102', 'C105', 'C106', 'C108', 'C114', 'C117', 'C120', 'C121', 'C122', 'C123', 'C125', 'C126', 'C127', 'C128', 'C129', 'C130',   
            'C131', 'C133', 'C134', 'C135', 'C136', 'C137', 'C138', 'C139', 'C140', 'C141', 'C142', 'C145', 'C146', 'C147', 'C148', 'C149',
            'C150', 'C151', 'C152', 'C153', 'C154', 'C155', 'C156', 'C157', 'C158', 'C159', 'C160', 'C161', 'C162', 'C163', 'C164'
        ]
        actual_year = today.year
        last_year = actual_year - 1
        dates = {
            1:('%s-11-01'%last_year,'%s-01-01'%actual_year),
            2:('%s-01-01'%actual_year,'%s-03-01'%actual_year),
            3:('%s-03-01'%actual_year,'%s-05-01'%actual_year),
            4:('%s-05-01'%actual_year,'%s-07-01'%actual_year),
            5:('%s-07-01'%actual_year,'%s-09-01'%actual_year),
            6:('%s-09-01'%actual_year,'%s-11-01'%actual_year),
        }
        start = dates[bimestre][0]
        one_day = datetime.timedelta(days=1)
        date_start = datetime.datetime.strptime(start, '%Y-%m-%d').date()
        date_stop = (datetime.datetime.strptime(dates[bimestre][1], '%Y-%m-%d') - one_day).date()
        stop  = date_stop.strftime('%Y-%m-%d')
        period_days = (date_stop-date_start).days + 1
        query = """
            SELECT SUM(l.total)
            FROM hr_payslip_line l LEFT JOIN hr_payslip p ON l.slip_id=p.id
            WHERE l.code IN %s AND p.date_from >= '%s' AND p.date_to <= '%s' AND l.employee_id = %s AND p.state != 'cancel' AND l.company_id = %s
        """%(tuple(CODES), start, stop, emp_id, self.env.company.id)
        self.env.cr.execute(query)
        amount_total = self.env.cr.fetchone()[0] or 0

        domain = [('x_employee_id','=',emp_id),('x_application','=','inasistencia'),('x_date_from_application','!=',False)]
        fields = ['x_date_from_application', 'x_date_to_application', 'x_duration', 'x_application']
        lines = self.env['x_social_security'].search_read(domain, fields) 
        msg = 'FALTAS\n'
        days_faltas = 0        


    def get_antig(self, emp_id, date=False, antig=0):
        today = datetime.datetime.today() #.date()
        date = date or today.date()
        employee = self.env['hr.employee'].search_read([('id','=',emp_id)], ['cfdi_date_contract'])
        if employee:
            antiguedad = employee[0]['cfdi_date_contract'] or today.date()
            antig = ((date - antiguedad).days + 1)/365 #.2425
        return antig

    def get_tvacdev(self, emp_id, date=False):
        #  Antigüedad          rango                  Vac. Deveng
        #1er año          0.00    1.00    6
        #2o año           1.00    2.00    8
        #3er año          2.00    3.00    10
        #4o año           3.00    4.00    12
        #5o al 9o año 4.00    9.00    14
        #10o al 14 año    9.00    14.00   16
        #15o al 19 año    14.00   19.00   18
        #20o al 24 año     16.00      24.00       20
        antig = self.get_antig(emp_id, date=False)
        if antig < 1:
            result = 6
        elif antig < 2:
            result = 8
        elif antig < 3:
            result = 10
        elif antig < 4:
            result = 12
        elif antig < 9:
            result = 14
        elif antig < 14:
            result = 16
        elif antig < 19:
            result = 18
        elif antig < 24:
            result = 20
        elif antig < 29:
            result = 22
        elif antig < 34:
            result = 24
        else:
            result = 26
        return result

    def get_fintegimss(self, emp_id, TVACDEV, DANT, debug2=False, date=False):
        company_registry = self.env.company.company_registry
        today = datetime.datetime.today() #.date()
        cfdi_date_contract = today.date()
        bono_antiguedad = 0
        record = self.env['hr.employee'].search_read([('id','=',emp_id)], ['cfdi_date_contract', 'bono_antiguedad'])
        if record:
            cfdi_date_contract = record[0]['cfdi_date_contract']
            bono_antiguedad = record[0]['bono_antiguedad']
        sueldo = 1
        dias_aguinaldo = 15
        antig = self.get_antig(emp_id, date=date) 
        if (company_registry == '12') and (antig > 1):
            dias_aguinaldo = 30
        aguinaldo = dias_aguinaldo/365 #.2425 # dias de aguinaldo 
        prima_vacacional = TVACDEV * 0.25/365 #.2425
        fondo_de_ahorro = 0.0000
        bono_x_antig = 0
        if DANT and company_registry in ('01', '02') and bono_antiguedad: # FRD and FDB
            bono_x_antig = DANT/365#.2425   
        fintegimss = sueldo + aguinaldo + bono_x_antig + prima_vacacional
        msg = ''
        if debug2:
            msg = u'A la Fecha: %s\nFecha Contrato: %s\nAntigüedad: %s\naguinaldo (15/365): %s\nBono: %s\nbono_x_antig: %s\nDANT: %s\nTVACDEV: %s\nprima_vacacional (TVACDEV * 0.25/365): %s\nfintegimss: %s'
            contract_date = cfdi_date_contract.strftime('%Y-%m-%d')
            msg = msg%(date, contract_date, antig, aguinaldo, bono_antiguedad, bono_x_antig, DANT, TVACDEV, prima_vacacional, fintegimss)
        return round(fintegimss, 7), msg        

    def get_dant(self, emp_id, date=False):
        # DANT_FORM Días para bono de antigüedad
        #Años         bono
        #0              0
        #1            0
        #2            5
        #3            5
        #4            10
        #5            10
        #6            15
        today = datetime.datetime.today() #.date()
        qty = 0
        if not date:
            date = today.date().replace(month=12, day=31)
        antig = self.get_antig(emp_id, date=date)
        if antig <2:
            qty = 0
        elif antig < 4:
            qty = 5
        elif antig < 6:
            qty = 10
        else:
            qty = 15
        return qty

    def get_uma(self, date=False):
        domain = [('type','=','01'), ('date','<=',date)]
        uma_id = self.env['l10n_mx_payroll.uma'].search(domain, order='date DESC', limit=1)
        return uma_id.amount

    # SDI_FORM Salario diario integrado para procesos
    def get_wage(self, employee_id, date=False):
        today = datetime.datetime.today() #.date()
        if not date:
            date = today.date()
        domain = [('employee_id','=',employee_id), ('effective_date','<=',date)] 
        return self.env['hr.employee.wage'].search(domain, order='effective_date DESC', limit=1)  


    def process_rules(self, emp_id, bimestre=False, sd=0, date=False, debug=False, debug2=False, debug_sdi=False, date_start=False, date_stop=False, complete=False, wage=False, move=False):  
        #process_rules(wiz.x_employee_id.id, sd=wiz.x_new_wage, date=wiz.x_date, debug=False, move=True)
        employee_id = self.env['hr.employee'].browse(emp_id)
        contract_id = self.env['hr.contract'].search([('employee_id','=',employee_id.id),('state','=','open')], limit=1)

        today = datetime.datetime.today() #.date()

        date = date_start or date or today.date()
        bimestre = bimestre or round((date.month+.1)/2.0)
        UMA = FACTOR = VARIMSS = SDI = SD = 0
        wage_act = False
        if wage:
            pass
        elif complete:
            date1 = (date_stop-datetime.timedelta(days=1))
            wage = self.get_wage(employee_id.id, date=date1)
            wage_act = self.get_wage(employee_id.id, date=today.date())
        else:
            wage = self.get_wage(employee_id.id, date)

        # UMA
        UMA = self.get_uma(date=date)
        # TVACDEV
        ddate = date
        if complete:
            ddate = date_stop
        TVACDEV = self.get_tvacdev(employee_id.id, date=ddate)
        # DANT
        DANT = self.get_dant(employee_id.id, date=ddate)
        # FINTEGIMSS
        FACTOR, msg = self.get_fintegimss(employee_id.id, TVACDEV, DANT, debug2, date)
        # VARIMSS
        VARIMSS, days_incapacidad, days_faltas, amount_total = 0.0, 0.0, 0.0, 0.0 # self.get_varimss(emp_id, bimestre, debug=debug)
        # SDI
        if sd:
            SD = sd
        elif complete:
            SD = wage_act.x_cfdi_sueldo_diario
        elif wage:
            SD = wage.x_cfdi_sueldo_diario
        despensa = SD * 0.06
        if SD * 0.06 > UMA:
            despensa = UMA
        despensa_integra = 0
        if employee_id.company_id.company_registry in ('01', '02'): # FRD and FDB
            if despensa > UMA*0.4:
                despensa_integra = (despensa - UMA*0.40) #/ SD
        SDI = round((SD * FACTOR + despensa_integra + VARIMSS),2)
        if debug_sdi:
            raise Warning('SD: %s\nSDI: %s\nFACTOR: %s\ndespensa_integra: %s\nVARIMSS: %s\n'%(SD, SDI, FACTOR, despensa_integra, VARIMSS))
        if complete:
            return UMA, FACTOR, VARIMSS, SDI, SD, days_incapacidad, days_faltas, amount_total
        elif debug:
            return UMA, FACTOR, VARIMSS, SDI, SD, TVACDEV, DANT
        elif debug2:
            params = VARIMSS, days_incapacidad, days_faltas, amount_total, SDI
            msg += '\nVARIMSS: %s\nincapacidad: %s\nfaltas: %s\namount_total: %s\nSDI: %s'%params
            raise Warning(msg)
        else:
            return UMA, FACTOR, VARIMSS, SDI, SD




"""
# employee_move
reason_id
send_imss
date_send_imss
dispmag
date_dispmag
category_ids

# wage
daily_wage
monthly_wage
variable_wage
factor
sdi
tab_id
current_tab_id
category_ids

# common
name
employee_id
employer_registration
workplace_id
company_id
currency_id
effective_date
state
"""
