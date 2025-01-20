# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import odoo
from odoo import api, fields, models, tools, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)

class TablaSubsidio(models.Model):
    _name = "l10n_mx_payroll.hr_tabla_subsidio"
    _description = "Tabla Subsidio"

    name = fields.Char(string=u"Año", required=True)
    limite_inferior = fields.Float(string=u"Limite inferior", required=True)
    limite_superior = fields.Float(string=u"Limite superior", required=True)
    subsidio = fields.Float(string="Subsidio", required=True)
    periodicidad = fields.Selection([('m','Mensual'),('q','Qincena'),('a','Anual')], string="Periodicidad", default='m')
