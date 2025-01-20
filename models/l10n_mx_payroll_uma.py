# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields, models, _

class TablaUmaUmiSmg(models.Model):
    _name = "l10n_mx_payroll.uma"
    _description = "Tabla UMA - UMI - SMG"

    name = fields.Char(string=u"Name", required=False)
    amount = fields.Float(string=u"Amount", required=True)
    date = fields.Date(string=u"Date", required=True)
    type = fields.Selection([
        ('01', 'UMA'),
        ('02', 'UMI'),
        ('03', 'SMG')
    ], string=u"UMA", default="01", required=False)
