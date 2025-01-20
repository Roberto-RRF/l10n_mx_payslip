# -*- encoding: utf-8 -*-

import logging
import base64
import json

from odoo import http
from odoo.http import content_disposition, request

CONTENT_MAXAGE = http.STATIC_CACHE_LONG  # menus, translations, static qweb

_logger = logging.getLogger(__name__)

class CfdiXmlController(http.Controller):

    @http.route('/cfdi/downloadxml/<string:unique>', type='http', auth="public")
    def cfdidownloadxml(self, unique, mods=None, lang=None):
        payslip = request.env["hr.payslip"].browse(int(unique))
        # content = p_id.l10n_mx_edi_content # l10n_mx_edi_compute_edi_content()
        content = payslip._l10n_mx_edi_create_xml_payslip()
        content = base64.decodebytes(content)
        report_name = payslip._get_report_base_filename()
        return request.make_response(content, [
            ('Content-Type', 'text/xml'),
            ('Cache-Control','public, max-age=' + str(CONTENT_MAXAGE)),
            ('Content-Disposition', content_disposition(report_name + '.xml')),
            ('Content-Length', len(content))
        ])
