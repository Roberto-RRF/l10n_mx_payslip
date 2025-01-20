# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.tools.xml_utils import _check_with_xsd

import logging
import logging.config
import base64
import re
from pytz import timezone
from lxml import etree
from datetime import datetime
from io import BytesIO
from zeep import Client
from zeep.transports import Transport

# TODO this code stop completly the loggin
"""
logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(name)s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'zeep.transports': {
            'level': 'DEBUG',
            'propagate': True,
            'handlers': ['console'],
        },
    }
})
"""
_logger = logging.getLogger(__name__)

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_mx_edi_finkok_sign(self, credentials, cfdi):
        ''' Send the CFDI XML document to Finkok for signature. Does not depend on a recordset
        '''
        try:
            transport = Transport(timeout=20)
            client = Client(credentials['sign_url'], transport=transport)
            response = client.service.stamp(cfdi, credentials['username'], credentials['password'])
        except Exception as e:
            return {
                'errors': [_("The Finkok service failed to sign with the following error: %s", str(e))],
            }

        if response.Incidencias and not response.xml:
            code = getattr(response.Incidencias.Incidencia[0], 'CodigoError', None)
            msg = getattr(response.Incidencias.Incidencia[0], 'MensajeIncidencia', None)
            extrainfo = getattr(response.Incidencias.Incidencia[0], 'ExtraInfo', None)
            if extrainfo:
                msg = "%s\n%s"%( msg, extrainfo )            
            errors = []
            if code:
                errors.append(_("Code : %s") % code)
            if msg:
                errors.append(_("Message : %s") % msg)
            return {'errors': errors}

        cfdi_signed = getattr(response, 'xml', None)
        if cfdi_signed:
            cfdi_signed = cfdi_signed.encode('utf-8')

        return {
            'cfdi_signed': cfdi_signed,
            'cfdi_encoding': 'str',
        }    

    def l10n_mx_edi_get_payslip_cfdi_values(self, payslip):
        def _format_string_cfdi(text, size=100):
            if not text:
                return None
            text = text.replace('|', ' ')
            return text.strip()[:size]

        def _format_float_cfdi(amount, precision):
            if amount is None or amount is False:
                return None
            return '%.*f' % (precision, amount)

        company = payslip.company_id
        supplier = company.partner_id
        currency_precision = payslip.currency_id.l10n_mx_edi_decimal_places

        if not payslip.l10n_mx_edi_post_time:
            payslip.set_l10n_mx_edi_post_time()

        cfdi_date = datetime.combine(
            fields.Datetime.from_string(payslip.invoice_date),
            payslip.l10n_mx_edi_post_time.time(),
        ).strftime('%Y-%m-%dT%H:%M:%S')

        if payslip.l10n_mx_edi_origin:
            origin_type, origin_uuids = payslip._l10n_mx_edi_read_cfdi_origin(payslip.l10n_mx_edi_origin)
        else:
            origin_type = None
            origin_uuids = []
        tz = self.env.user.tz
        fecha_utc =  datetime.now(timezone("UTC"))
        local_date = fecha_utc.astimezone(timezone(tz)).strftime("%Y-%m-%dT%H:%M:%S")
        local_year = int(local_date.split("-")[0])

        payslip_number = (payslip.number or '').replace('/', '').replace('-', '')
        name_numbers = list(re.finditer(r'\d+', payslip_number))

        # 'certificate': certificate,
        # 'certificate_number': certificate.serial_number,
        # 'certificate_key': certificate.sudo().get_data()[0].decode('utf-8'),
        cfdi_values = {
            **payslip.l10n_mx_edi_get_common_cfdi_values(),
            'record': payslip,
            'currency_precision': currency_precision,

            'cfdi_date': cfdi_date,
            'format_string': _format_string_cfdi,
            'format_float': _format_float_cfdi,
            'issued_address': payslip._get_l10n_mx_edi_issued_address(),
            'supplier': supplier,
            'customer': payslip.employee_id,

            'origin_type': origin_type,
            'origin_uuids': origin_uuids,
            'local_date': local_date,
            'compensacion_saldos_favor': "%s"%(local_year-1),
            'ultimo_sueldo_mensual': payslip._get_salary_line_total('SD') * 30,

            'serie_number': re.sub(r'\W+', '', payslip_number[:name_numbers[-1].start()]),
            'folio_number': name_numbers[-1].group(),
        }
        return cfdi_values    










































    def _l10n_mx_edi_get_payslip_templates_OLD(self, payslip):
        version = payslip.l10n_mx_edi_version
        return self.env.ref('l10n_mx_payslip.cfdipayslipv%s'%(version.replace('.', ''))), self.sudo().env.ref('l10n_mx_edi.xsd_cached_cfdv%s_xsd'%(version.replace('.', '')), False)    

    def _l10n_mx_edi_export_payslip_cfdi_OLD(self, payslip):
        ''' Create the CFDI attachment for the invoice passed as parameter.
        :param move:    An account.move record.
        :return:        A dictionary with one of the following key:
        * cfdi_str:     A string of the unsigned cfdi of the invoice.
        * error:        An error if the cfdi was not successfuly generated.
        '''
        # == CFDI values ==
        qweb_template, xsd_attachment = self._l10n_mx_edi_get_payslip_templates(payslip)

        cfdi_values = self.l10n_mx_edi_get_payslip_cfdi_values(payslip)
        cfdi = qweb_template._render(cfdi_values)
        cfdi = b' '.join(cfdi.split())
        _logger.info('---- _l10n_mx_edi_export_payslip_cfdi XML TEST %s '%(cfdi) )

        decoded_cfdi_values = payslip._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi)
        cfdi_cadena_crypted = cfdi_values['certificate'].sudo().get_encrypted_cadena(decoded_cfdi_values['cadena'])
        decoded_cfdi_values['cfdi_node'].attrib['Sello'] = cfdi_cadena_crypted
        xml_str = etree.tostring(decoded_cfdi_values['cfdi_node'], pretty_print=True, xml_declaration=True, encoding='UTF-8')

        # == Optional check using the XSD ==
        xsd_datas = base64.b64decode(xsd_attachment.datas) if xsd_attachment else None
        if xsd_datas:
            try:
                with BytesIO(xsd_datas) as xsd:
                    _check_with_xsd(decoded_cfdi_values['cfdi_node'], xsd)
            except (IOError, ValueError):
                _logger.info(_('The xsd file to validate the XML structure was not found'))
            except Exception as e:
                return {'errors': str(e).split('\\n'), 'cfdi_str': xml_str}
        return {
            'cfdi_str': xml_str
        }

    def _l10n_mx_edi_finkok_cancel_payslip(self, move, credentials, cfdi):
        return self._l10n_mx_edi_finkok_cancel_service(
            move.l10n_mx_edi_cfdi_uuid_canceled, 
            move.company_id, 
            credentials,
            uuid_replace=move.l10n_mx_edi_cfdi_uuid
        )

    def _l10n_mx_edi_solfact_cancel_payslip(self, move, credentials, cfdi):
        return self._l10n_mx_edi_solfact_cancel_service(
            move.l10n_mx_edi_cfdi_uuid_canceled, 
            move.company_id, 
            credentials,
            uuid_replace=move.l10n_mx_edi_cfdi_uuid
        )
