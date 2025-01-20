# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import MissingError, UserError, ValidationError, AccessError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.tools.float_utils import float_compare

import base64
from collections import defaultdict
import functools
import logging

from pytz import timezone

_logger = logging.getLogger(__name__)


class EdiExportDataCategory(models.Model):
    _name = "edi.data.configuration.category"
    _description = "EDI Export Category"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char('Name', index='trigram', required=True)
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name', recursive=True,
        store=True)    
    parent_id = fields.Many2one(
        'edi.data.configuration.category', 'Parent Category', 
        index=True, ondelete='cascade')
    parent_path = fields.Char(index=True, unaccent=False)
    child_id = fields.One2many(
        'edi.data.configuration.category', 'parent_id', 'Child Categories')
    edidata_count = fields.Integer(
        '# Datas XML', compute='_compute_edidatas_count',
        help="The number of products under this category (Does not consider the children categories)")

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    def _compute_edidatas_count(self):
        read_group_res = self.env['edi.data.configuration.xml.line'].read_group([('categ_id', 'child_of', self.ids)], ['categ_id'], ['categ_id'])
        group_data = dict((data['categ_id'][0], data['categ_id_count']) for data in read_group_res)
        for categ in self:
            edidata_count = 0
            for sub_categ_id in categ.search([('id', 'child_of', categ.ids)]).ids:
                edidata_count += group_data.get(sub_categ_id, 0)
            categ.edidata_count = edidata_count

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive categories.'))
        return True

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    def unlink(self):
        # main_category = self.env.ref('product.product_category_all')
        # if main_category in self:
        #     raise UserError(_("You cannot delete this product category, it is the default generic category."))
        return super().unlink()            


class EdiExportData(models.Model):
    _name = 'edi.data.configuration.xml'
    _description = 'EDI Export DATA'
    _order = 'sequence,name'    

    name = fields.Char(string="Name")
    company_id = fields.Many2one('res.company', 
        string='Company', readonly=True, copy=False, required=True,
        default=lambda self: self.env.company)

    # Generic
    sequence = fields.Integer(default=5,
        help="When dealing with multiple actions, the execution order is "
            "based on the sequence. Low number means high priority.")
    model_id = fields.Many2one(comodel_name='ir.model',
        string="Models", help="Indicate the model to export data.")
    model_name = fields.Char(related='model_id.model', 
        string='Model Name', readonly=True, store=True)

    # --- 
    line_ids = fields.One2many('edi.data.configuration.xml.line', 
        'export_id', string='Configuration Items', copy=True)
    active = fields.Boolean(string='Active')

    def compute_export_data(self, localdict={}):
        self.ensure_one()
        res = False
        for rule in sorted(self.line_ids, key=lambda x: x.sequence):
            amount = rule._compute_rule(localdict)
            localdict[rule.code] = amount
            localdict['xmldatas'].dict[rule.code] = amount
        return localdict['xmldatas'].dict

class EdiExportDataLine(models.Model):
    _name = 'edi.data.configuration.xml.line'
    _description = 'EDI Export DATa Line'

    def _read_group_categ_id(self, categories, domain, order):
        category_ids = self.env.context.get('default_categ_id')
        if not category_ids and self.env.context.get('group_expand'):
            category_ids = categories._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return categories.browse(category_ids)

    DEFAULT_PYTHON_CODE = '''
# Available variables:
#----------------------
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days
# inputs: object containing the computed inputs.

# Note: returned value have to be set in the variable 'result'

result = rules.NET > categories.NET * 0.10'''  

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    export_id = fields.Many2one('edi.data.configuration.xml', 
        string='Configuration Entry', ondelete="cascade",
        help="The Configuration XML of this entry line.", 
        index=True, required=True, auto_join=True)
    required = fields.Boolean()
    sequence = fields.Integer('Sequence')
    categ_id = fields.Many2one(
        'edi.data.configuration.category', 'Edi Data Category',
        change_default=True, group_expand='_read_group_categ_id',
        required=True, help="Select category for the current product")    

    default_type = fields.Selection([
        ('text', 'Text'),
        ('python', 'Python'),
    ], string='Default Type', default="python")
    default = fields.Char(string="Default Value")
    default_python = fields.Text(string="Default Python", 
        default=DEFAULT_PYTHON_CODE)
    default_help = fields.Char(string="Help text")

    @api.constrains('default_python')
    def _check_python_code(self):
        for action in self.sudo().filtered('default_python'):
            msg = test_python_expr(expr=action.code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    def _compute_rule(self, localdict):
        self.ensure_one()
        if self.default_type == 'text':
            return self.default
        if self.default_type == 'python':
            safe_eval(self.default_python, localdict, mode='exec', nocopy=True)
            return localdict.get('result', False)
