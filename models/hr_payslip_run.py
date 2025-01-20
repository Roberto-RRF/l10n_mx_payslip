# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import threading
import logging
from datetime import datetime
from pytz import timezone
from datetime import date, datetime, time

import odoo
from odoo import models, fields, _, registry, api, SUPERUSER_ID
from odoo.tools import config, split_every
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CFDI_XSLT_CADENA = 'l10n_mx_edi/data/3.3/cadenaoriginal.xslt'
CFDI_XSLT_CADENA_TFD = 'l10n_mx_edi/data/xslt/3.3/cadenaoriginal_TFD_1_1.xslt'

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    cfdi_date_payment = fields.Date(string="Fecha pago", required=True, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    struct_id = fields.Many2one('hr.payroll.structure', string='Structure',
        readonly=True,
        help='Defines the rules that have to be applied to this payslip, accordingly '
             'to the contract chosen. If you let empty the field contract, this field isn\'t '
             'mandatory anymore and thus the rules applied will be all the rules set on the '
             'structure of all contracts of the employee valid for the chosen period')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    l10n_mx_edi_canceled = fields.Boolean(string="Cancelado", default=False)
    l10n_mx_edi_validated = fields.Boolean(string="Validado", default=False)
    l10n_mx_edi_sendemail = fields.Boolean(string="Send Email", default=False)
    payslip_run_closed = fields.Boolean(string="Cerrada", default=False)    

    def _message_button_hook(self, new_message=""):
        tz = timezone('America/Monterrey')
        new_date = fields.Datetime.to_string(datetime.now(tz))
        new_message = new_message + new_date
        odoobot = self.env.ref('base.partner_root')
        self.message_post(body=_(new_message),
                          message_type='comment',
                          subtype_xmlid='mail.mt_note',
                          author_id=odoobot.id)
        self._cr.commit()
        return True

    #--------------------------------------
    # Actualizados:
    #--------------------------------------

    #---------------------------------------
    #  Calcular Nominas
    #---------------------------------------
    def _action_compute_sheets_threading(self, run_id=False):
        self.env.flush_all()
        dbname = self._cr.dbname
        with registry(dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            RunModel = env['hr.payslip.run']
            PayslipModel = env['hr.payslip']

            run_obj = RunModel.browse( run_id )
            run_obj._message_button_hook('Inicia Calcular Nomina ')
            domain = [('state', 'in', ['draft', 'verify']), ('payslip_run_id', '=', run_id)]
            payslip_to_assign = PayslipModel.search_read(domain, ["name"], limit=None, order='number desc, id asc')
            payslip_to_assign_ids = [p_id["id"] for p_id in payslip_to_assign ]
            _logger.info("----- PAYSLIP-RUN calcular total %s "%(len(payslip_to_assign_ids)))
            for batched_to_compute in split_every(30, payslip_to_assign_ids, PayslipModel.browse):
                try:
                    batched_to_compute.compute_sheet()
                    _logger.info("----- PAYSLIP-RUN calcular %s "%(len(batched_to_compute)))
                except Exception as e:
                    msg = 'Error al Calcular Nomina %s %s '%( batched_to_compute.ids, e )
                    run_obj._message_button_hook(msg)
            run_obj._message_button_hook('Termina Calcular Nomina ')

    def action_compute_sheets(self):
        run_id = self.id
        threaded_compute = threading.Thread(target=self._action_compute_sheets_threading, args=([run_id]))
        threaded_compute.start()
        threaded_compute.join()
        return {}

    def action_close_run(self):
        self.write({'payslip_run_closed': True})

    def action_send_email(self):
        self.ensure_one()
        self.l10n_mx_edi_sendemail = True
        # payslip_ids = self.env["hr.payslip"].search([('state', '=', 'done'), ('l10n_mx_edi_sendemail', '=', False), ('payslip_run_id', '=', self.id), ('payslip_run_id.l10n_mx_edi_sendemail', '=', True)])
        _logger.info("--- Payroll trigger of send mail cron ")
        self = self.with_context(run_id=self.id)
        trigger = self.env.ref('l10n_mx_payslip.ir_cron_payroll_send_email_cfdi')
        # trigger._try_lock()
        try:
           trigger.sudo().with_context(run_id=self.id).method_direct_trigger() 
        except Exception as e:
            _logger.warning("Lock acquiring failed, cron payroll is already running %s "%(e) )
            return
        return False

    def action_validate(self):
        self.ensure_one()
        payslip_ids = self.env["hr.payslip"].search([('state', '=', 'verify'), ('payslip_run_id', '=', self.id)])
        payslip_ids.write({'l10n_mx_edi_xmlcfdi': True})
        _logger.info("--- Payroll trigger of the validate cron")
        try:
            trigger = self.env.ref('l10n_mx_payslip.ir_cron_payroll_generate_xml_cfdi')
            trigger.sudo().method_direct_trigger()
        except Exception as e:
            _logger.warning("Lock acquiring failed, cron payroll is already running %s "%(e) )
            return
        return False































    #---------------------------------------
    #  Enviar Email
    #---------------------------------------
    def _enviar_nomina_scheduler_tasks_OLD(self, use_new_cursor=False, run_id=False):
        domain = [('state', '=', 'done'), ('payslip_run_id', '=', run_id), ('l10n_mx_edi_sendemail', '=', False)]
        payslip_to_assign = self.env['hr.payslip'].search(domain, limit=None, order='number desc, id asc')
        for payslip_chunk in split_every(1, payslip_to_assign.ids):
            _logger.info('-------- Enviar Email Nomina %s '%( payslip_chunk )  )
            res = self.env['hr.payslip'].browse(payslip_chunk)._generate_pdf()
            try:
                if use_new_cursor:
                    self._cr.commit()
            except Exception as e:
                _logger.info('-------- Error al Enviar Email Nomina %s %s '%( payslip_chunk, e ) )
        if use_new_cursor:
            self._cr.commit()
    def _enviar_nomina_threading_task_OLD(self, use_new_cursor=False, run_id=False):
        try:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))  # TDE FIXME
            self._enviar_nomina_scheduler_tasks(use_new_cursor=use_new_cursor, run_id=run_id)
        finally:
            if use_new_cursor:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return {}
    def _enviar_nomina_threading_OLD(self, run_id=False):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            self.env['hr.payslip.run']._enviar_nomina_threading_task(use_new_cursor=self._cr.dbname, run_id=run_id)
            new_cr.close()
            return {}
    def action_send_email_OLD(self):
        run_id = self.id
        threaded_email = threading.Thread(target=self._enviar_nomina_threading, args=([run_id]))
        threaded_email.start()
        threaded_email.join()
        return {}



    #---------------------------------------
    #  Confirmar y Timbrar Nominas
    #---------------------------------------
    def confirm_sheet_run_scheduler_tasks_OLD(self, use_new_cursor=False, run_id=False):
        cr = self._cr
        errors = {}
        payslipModel = self.env['hr.payslip']
        for payslip_id in payslipModel.search([('payslip_run_id', '=', run_id)]):
            try:
                cr.execute('SAVEPOINT model_payslip_confirm_cfdi_save')
                payslip = payslipModel.browse(payslip_id.id)
                if payslip.state in ['draft','verify']:
                    payslip.action_payslip_done()
                # if not payslip.l10n_mx_cfdi_uuid and payslip.cfdi_total > 0:
                #     res = payslip.action_payslip_done()
                cr.execute('RELEASE SAVEPOINT model_payslip_confirm_cfdi_save')
            except Exception as e:
                errors[ payslip_id ] = '%s'%(e)
                cr.execute('ROLLBACK TO SAVEPOINT model_payslip_confirm_cfdi_save')
                pass
            if use_new_cursor:
                self._cr.commit()
        for error in errors:
            if isinstance(error,int):
                payslip_ids = payslipModel.browse( error )
            else:
                payslip_ids = error
            for payslip_id in payslip_ids:
                if errors.get( payslip_id.id ):
                    payslip_id.message_post(
                        body='%s'%( errors[ payslip_id.id ] )
                    )
        self.action_close()
    @api.model
    def _confirm_sheet_run_task_OLD(self, use_new_cursor=False, run_id=False):
        try:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))  # TDE FIXME
            self.confirm_sheet_run_scheduler_tasks(use_new_cursor=use_new_cursor, run_id=run_id)
        finally:
            if use_new_cursor:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return {}
    def _confirm_sheet_run_threading_OLD(self, run_id=False):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            self.env['hr.payslip.run']._confirm_sheet_run_task(use_new_cursor=self._cr.dbname, run_id=run_id)
            new_cr.close()
            return {}
    def _confirm_sheet_run_date_OLD(self):
        ids = self.ids
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            Payslip = self.sudo().env['hr.payslip']
            lines = Payslip.search([('payslip_run_id', 'in', ids), ('l10n_mx_edi_post_time', '=', False)])
            for line in lines:
                line.set_l10n_mx_edi_post_time()
                new_cr.commit()
        return {}
    def action_validate_OLD(self):
        if not self.l10n_mx_edi_validated:
            run_id = self.id
            # Escribe fecha
            threaded_date = threading.Thread(target=self._confirm_sheet_run_date, args=(), name='date_%s'%run_id)
            threaded_date.start()
            threaded_date.join()
            threaded_validate = threading.Thread(target=self._confirm_sheet_run_threading, args=([run_id]))
            threaded_validate.start()
            threaded_validate.join()
            self.l10n_mx_edi_validated = True
        return {}

    #---------------------------------------
    #  Cancelar Nominas
    #---------------------------------------
    def cancel_sheet_run_scheduler_tasks_OLD(self, use_new_cursor=False, run_id=False, reason_cancel=False):
        cr = self._cr
        errors = {}
        payslipModel = self.env['hr.payslip']
        run_obj = self.browse( run_id )
        run_obj._message_button_hook('Inicia Cancelación de Recibos.')
        for payslip in payslipModel.search([('payslip_run_id', '=', run_id)]):
            try:
                cr.execute('SAVEPOINT model_payslip_confirm_cfdi_save')
                payslip.with_context(reason_cancel=reason_cancel).button_cancel_xml()
                cr.execute('RELEASE SAVEPOINT model_payslip_confirm_cfdi_save')
            except Exception as e:
                errors[ payslip_id ] = '%s'%(e)
                run_obj._message_button_hook('Error en Cancelación de Recibos:\n%s'%e)
                cr.execute('ROLLBACK TO SAVEPOINT model_payslip_confirm_cfdi_save')
                pass
            if use_new_cursor:
                self._cr.commit()
        run_obj._message_button_hook('Termina Cancelación de Recibos.')
        for error in errors:
            if isinstance(error,int):
                payslip_ids = payslipModel.browse( error )
            else:
                payslip_ids = error
            for payslip_id in payslip_ids:
                if errors.get( payslip_id.id ):
                    payslip_id.message_post(
                        body='%s'%( errors[ payslip_id.id ] )
                    )
        self.action_close()
    @api.model
    def _cancel_sheet_run_task_OLD(self, use_new_cursor=False, run_id=False, reason_cancel=False):
        try:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))  # TDE FIXME
            self.cancel_sheet_run_scheduler_tasks(use_new_cursor=use_new_cursor, run_id=run_id, reason_cancel=reason_cancel)
        finally:
            if use_new_cursor:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return {}
    def _cancel_sheet_run_threading_OLD(self, run_id=False, reason_cancel=False):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            self.env['hr.payslip.run']._cancel_sheet_run_task(use_new_cursor=self._cr.dbname, run_id=run_id, reason_cancel=reason_cancel)
            new_cr.close()
            return {}
    def action_payslip_cancel_xml_OLD(self, reason_cancel):
        run_id = self.id
        threaded_cancel = threading.Thread(target=self._cancel_sheet_run_threading, args=(run_id, reason_cancel)) 
        threaded_cancel.start()
        threaded_cancel.join()
        self.l10n_mx_edi_canceled = True
        return {}
    def button_cancel_xml_OLD(self):
        action = self.env.ref('l10n_mx_payslip.hr_payslip_reason_cancel_action').read([])[0]
        return action

    #---------------------------------------
    #  Borrar Nominas en Ceros
    #---------------------------------------
    def _unlink_sheet_run_threading_task_OLD(self, use_new_cursor=False, active_id=False):
        try:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))  # TDE FIXME
            runModel = self.env['hr.payslip.run']
            payslipModel = self.env['hr.payslip']
            for run_id in runModel.browse(active_id):
                payslip_ids = payslipModel.search([('state', 'in', ['draft']), ('payslip_run_id', '=', run_id.id)])
                line_ids = payslip_ids.filtered(lambda line: line._get_salary_line_total('C99') == 0.0)
                _logger.info('-------- Payslip  Unlik %s '%( len(line_ids) ) )
                for payslip in line_ids:
                    try:
                        _logger.info('------- Payslip Unlink %s '%(payslip.id) )
                        payslip.unlink()
                    except Exception as e:
                        payslip.message_post(body='Error Al borrar la Nomina: %s '%( e ) )
                        _logger.info('------ Error Al borrar  la Nomina %s '%( e ) )
                    if use_new_cursor:
                        self._cr.commit()
        finally:
            if use_new_cursor:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return {}
    def _unlink_sheet_run_threading_OLD(self, active_id):
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            self.env['hr.payslip.run']._unlink_sheet_run_threading_task(use_new_cursor=self._cr.dbname, active_id=active_id)
            new_cr.close()
        return {}
    def action_unlink_sheets_OLD(self):
        for run_id in self:
            threaded_calculation = threading.Thread(target=self._unlink_sheet_run_threading, args=(run_id.id, ), name='unlinknominarunid_%s'%run_id.id)
            threaded_calculation.start()
            threaded_calculation.join()
        return {}
