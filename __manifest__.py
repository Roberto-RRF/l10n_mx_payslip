# -*- coding: utf-8 -*-
# Part of OpenBIAS. See LICENSE file for full copyright and licensing details.
{
    'name': "CFDI MX Payroll",
    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    'description': """
        Long description of module's purpose
    """,
    'author': "OpenBias",
    'website': "https://bias.com.mx",
    'category': 'Uncategorized',
    'version': '17.0.0.7',
    'depends': [
        'base_setup', 
        'hr_payroll', 
        'hr_payroll_account', 
        'account_accountant', 
        'l10n_mx_edi',
        'account_edi',
        'hr_recruitment',
    ],
    'demo': [
        'data/hr_demo.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_payroll_security.xml',
        'data/ir_cron_data.xml',
        'data/edi_data_configuration_data.xml',
        'data/data_report.xml',
        'data/hr_payslip.sql',
        #'views/report_templates.xml',
        'views/edi_data_configuration_views.xml',

        # 'views/hr_payslip_line_views.xml',
        'views/hr_payroll_structure_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payroll_views.xml',
        'views/l10n_mx_payroll_regpat_views.xml',
        'views/l10n_mx_payroll_hr_tabla_isr_views.xml',
        'views/l10n_mx_payroll_hr_tabla_subsidio_views.xml',
        'views/l10n_mx_payroll_uma_views.xml',
        'views/hr_job_views.xml',
        'views/hr_payslip_views.xml',
        'views/cfdi_models_menus.xml',
        'views/res_config_settings_views.xml',
        'views/l10n_mx_payslip_uuid_history_views.xml',
        'views/hr_employee_move_type_views.xml',
        'views/hr_employee_move_views.xml',
        'views/motivation_motivation_views.xml',
        'views/hr_menus_views.xml',
        'wizard/hr_payroll_payslips_by_employees_views.xml',
        'wizard/hr_payroll_payslips_reason_cancel_views.xml',
        'wizard/hr_employee_move_wiz_views.xml',
        'report/report_payslip_xml.xml',
        'data/mail_template_data.xml',
        'data/3.3/cfdi.xml',
        'data/4.0/cfdi.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_mx_payslip/static/src/scss/layout_nomina.scss',
        ],
    },
    'license': 'Other proprietary',

}
