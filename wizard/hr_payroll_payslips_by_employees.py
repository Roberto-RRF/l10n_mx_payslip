# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from collections import defaultdict
from datetime import datetime, date, time
import pytz

from odoo import models, fields, _, registry, api, SUPERUSER_ID
from odoo.exceptions import UserError

# import threading
from threading import Thread

_logger = logging.getLogger(__name__)

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    def _get_employees(self):
        return []

    def _get_structure(self):
        active_id = self.env.context.get('active_id', False)
        if active_id:
            payslip_run_id = self.env['hr.payslip.run'].browse(active_id)
            return payslip_run_id.struct_id and payslip_run_id.struct_id or False

    structure_id = fields.Many2one('hr.payroll.structure', string='Salary Structure', default=lambda self: self._get_structure())
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)    

    def processCalculationEmployees(self, wiz_id=False, payslip_run_id=False, structure_id=False, employees=False):
        self.env.flush_all()
        dbname = self._cr.dbname
        with registry(dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            payslips = env['hr.payslip']
            Payslip = env['hr.payslip']
            PayslipEmployees = env['hr.payslip.employees']
            HrWorkEntry = env['hr.work.entry']
            PayslipRun = env['hr.payslip.run']
            EmployeeModel = env['hr.employee']

            default_values = Payslip.default_get(Payslip.fields_get())

            rec_id = PayslipEmployees.browse(wiz_id)
            payslip_run = PayslipRun.browse(payslip_run_id)
            for employees in EmployeeModel.browse( employees ):
                contracts = employees._get_contracts(
                    payslip_run.date_start, payslip_run.date_end, states=['open', 'close']
                ).filtered(lambda c: c.active)
                contracts.generate_work_entries(payslip_run.date_start, payslip_run.date_end)
                work_entries = HrWorkEntry.search([
                    ('date_start', '<=', payslip_run.date_end),
                    ('date_stop', '>=', payslip_run.date_start),
                    ('employee_id', 'in', employees.ids),
                ])
                rec_id._check_undefined_slots(work_entries, payslip_run)
                if(rec_id.structure_id.type_id.default_struct_id == rec_id.structure_id):
                    work_entries = work_entries.filtered(lambda work_entry: work_entry.state != 'validated')
                    if work_entries._check_if_error():
                        work_entries_by_contract = defaultdict(lambda: HrWorkEntry)

                        for work_entry in work_entries.filtered(lambda w: w.state == 'conflict'):
                            work_entries_by_contract[work_entry.contract_id] |= work_entry

                        for contract, work_entries in work_entries_by_contract.items():
                            conflicts = work_entries._to_intervals()
                            time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in conflicts._items]])
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Some work entries could not be validated.'),
                                'message': _('Time intervals to look for:%s', time_intervals_str),
                                'sticky': False,
                            }
                        }

                payslips_vals = []
                for contract in self._filter_contracts(contracts):
                    values = dict(default_values, **{
                        'name': _('New Payslip'),
                        'employee_id': contract.employee_id.id,
                        'payslip_run_id': payslip_run.id,
                        'date_from': payslip_run.date_start,
                        'date_to': payslip_run.date_end,
                        'contract_id': contract.id,
                        'struct_id': rec_id.structure_id.id or contract.structure_type_id.default_struct_id.id,
                        'company_id': rec_id.company_id and rec_id.company_id.id or payslip_run.company_id.id,
                    })
                    payslips_vals.append(values)
                payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)
                env.cr.commit()
                payslips._compute_name()
                payslips.compute_sheet()
                payslip_run.state = 'verify'

        return {}

    def compute_sheet_bath(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            today = fields.date.today()
            first_day = today + relativedelta(day=1)
            last_day = today + relativedelta(day=31)
            if from_date == first_day and end_date == last_day:
                batch_name = from_date.strftime('%B %Y')
            else:
                batch_name = _('From %s to %s', format_date(self.env, from_date), format_date(self.env, end_date))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': batch_name,
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        employees = self.with_context(active_test=False).employee_ids
        if not employees:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        #Prevent a payslip_run from having multiple payslips for the same employee
        employees -= payslip_run.slip_ids.employee_id
        active_id = self.env.context.get('active_id')
        structure_id = self.structure_id and self.structure_id.id or False
        Thread(target=self.processCalculationEmployees, args=(self.id, active_id, structure_id, employees.ids)).start()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
