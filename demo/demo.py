
# Actualiza Valores Positivos
UPDATE hr_salary_rule hsr
SET cfdi_tipo = (
        SELECT 
            CASE 
                WHEN t.name = 'Percepciones' THEN 'p'
                WHEN t.name = 'Deducciones' THEN 'd'
                WHEN t.name = 'Otro pago' THEN 'o'
                WHEN t.name = 'Incapacidades' THEN 'i'
            ELSE '' END AS "tipo"
        FROM l10n_mx_payroll_tipo t WHERE t.id = hsr.cfdi_tipo_id
    )
WHERE hsr.cfdi_tipo_id is not Null;


# Actualiza Valores Negativos
UPDATE hr_salary_rule hsr
SET cfdi_tipo_neg = (
    SELECT 
        CASE 
            WHEN t.name = 'Percepciones' THEN 'p'
            WHEN t.name = 'Deducciones' THEN 'd'
            WHEN t.name = 'Otro pago' THEN 'o'
            WHEN t.name = 'Incapacidades' THEN 'i'
        ELSE '' END AS "tipo"
    FROM l10n_mx_payroll_tipo t WHERE t.id = hsr.cfdi_tipo_neg_id
    )
WHERE hsr.cfdi_tipo_neg_id is not Null;



# Actualiza Valores Positivos Codigo Agrupador
UPDATE hr_salary_rule hsr
SET 
    cfdi_tipo_percepcion = (
        SELECT 
            COALESCE(agr.code, Null)
        FROM l10n_mx_payroll_codigo_agrupador agr
        LEFT JOIN l10n_mx_payroll_tipo tip ON (agr.cfdi_tipo_id = tip.id)
        WHERE agr.id = hsr.cfdi_codigoagrupador_id AND tip.id = hsr.cfdi_tipo_id AND tip.name = 'Percepciones'
    ),
    cfdi_tipo_deduccion = (
        SELECT 
            COALESCE(agr.code, Null)
        FROM l10n_mx_payroll_codigo_agrupador agr
        LEFT JOIN l10n_mx_payroll_tipo tip ON (agr.cfdi_tipo_id = tip.id)
        WHERE agr.id = hsr.cfdi_codigoagrupador_id AND tip.id = hsr.cfdi_tipo_id AND tip.name = 'Deducciones'
    ),
    cfdi_tipo_otrospagos = (
        SELECT 
            COALESCE(agr.code, Null)
        FROM l10n_mx_payroll_codigo_agrupador agr
        LEFT JOIN l10n_mx_payroll_tipo tip ON (agr.cfdi_tipo_id = tip.id)
        WHERE agr.id = hsr.cfdi_codigoagrupador_id AND tip.id = hsr.cfdi_tipo_id AND tip.name = 'Otro pago'
    ),
    cfdi_tipo_incapacidad = (
        SELECT 
            COALESCE(agr.code, Null)
        FROM l10n_mx_payroll_codigo_agrupador agr
        LEFT JOIN l10n_mx_payroll_tipo tip ON (agr.cfdi_tipo_id = tip.id)
        WHERE agr.id = hsr.cfdi_codigoagrupador_id AND tip.id = hsr.cfdi_tipo_id AND tip.name = 'Incapacidades'
    )
WHERE hsr.cfdi_tipo_id is not Null AND hsr.cfdi_codigoagrupador_id is not Null;


UPDATE hr_salary_rule hsr
SET 
    cfdi_tipo_percepcion_neg = (
        SELECT 
            COALESCE(agr.code, Null)
        FROM l10n_mx_payroll_codigo_agrupador agr
        LEFT JOIN l10n_mx_payroll_tipo tip ON (agr.cfdi_tipo_id = tip.id)
        WHERE agr.id = hsr.cfdi_codigoagrupador_neg_id AND tip.id = hsr.cfdi_tipo_neg_id AND tip.name = 'Percepciones'
    ),
    cfdi_tipo_deduccion_neg = (
        SELECT 
            COALESCE(agr.code, Null)
        FROM l10n_mx_payroll_codigo_agrupador agr
        LEFT JOIN l10n_mx_payroll_tipo tip ON (agr.cfdi_tipo_id = tip.id)
        WHERE agr.id = hsr.cfdi_codigoagrupador_neg_id AND tip.id = hsr.cfdi_tipo_neg_id AND tip.name = 'Deducciones'
    ),
    cfdi_tipo_otrospagos_neg = (
        SELECT 
            COALESCE(agr.code, Null)
        FROM l10n_mx_payroll_codigo_agrupador agr
        LEFT JOIN l10n_mx_payroll_tipo tip ON (agr.cfdi_tipo_id = tip.id)
        WHERE agr.id = hsr.cfdi_codigoagrupador_neg_id AND tip.id = hsr.cfdi_tipo_neg_id AND tip.name = 'Otro pago'
    ),
    cfdi_tipo_incapacidad_neg = (
        SELECT 
            COALESCE(agr.code, Null)
        FROM l10n_mx_payroll_codigo_agrupador agr
        LEFT JOIN l10n_mx_payroll_tipo tip ON (agr.cfdi_tipo_id = tip.id)
        WHERE agr.id = hsr.cfdi_codigoagrupador_neg_id AND tip.id = hsr.cfdi_tipo_neg_id AND tip.name = 'Incapacidades'
    )
WHERE hsr.cfdi_tipo_neg_id is not Null AND hsr.cfdi_codigoagrupador_neg_id is not Null;







# Activar envio de correos masivos:
domain = [('state', '=', 'done'), ('payslip_run_id', '=', record.id), ('l10n_mx_edi_sendemail', '=', True)]
payslip_ids = env['hr.payslip'].search(domain, limit=None, order='number desc, id asc')
payslip_ids.update({
    'l10n_mx_edi_sendemail': False
})






#- Pruebas

    def l10n_mx_edi_update_sat_status(self):
        '''Synchronize both systems: Odoo & SAT to make sure the invoice is valid.
        '''
        url = 'https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl'
        headers = {'SOAPAction': 'http://tempuri.org/IConsultaCFDIService/Consulta', 'Content-Type': 'text/xml; charset=utf-8'}
        template = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:ns0="http://tempuri.org/" xmlns:ns1="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
   <SOAP-ENV:Header/>
   <ns1:Body>
      <ns0:Consulta>
         <ns0:expresionImpresa>${data}</ns0:expresionImpresa>
      </ns0:Consulta>
   </ns1:Body>
</SOAP-ENV:Envelope>"""
        namespace = {'a': 'http://schemas.datacontract.org/2004/07/Sat.Cfdi.Negocio.ConsultaCfdi.Servicio'}
        for move in self:
            supplier_rfc = move.l10n_mx_edi_cfdi_supplier_rfc
            customer_rfc = move.l10n_mx_edi_cfdi_customer_rfc
            total = float_repr(move.l10n_mx_edi_cfdi_amount, precision_digits=move.currency_id.decimal_places)
            uuid = move.l10n_mx_edi_cfdi_uuid
            params = '?re=%s&amp;rr=%s&amp;tt=%s&amp;id=%s' % (
                tools.html_escape(tools.html_escape(supplier_rfc or '')),
                tools.html_escape(tools.html_escape(customer_rfc or '')),
                total or 0.0, uuid or '')
            soap_env = template.format(data=params)
            try:
                soap_xml = requests.post(url, data=soap_env, headers=headers, timeout=20)
                response = fromstring(soap_xml.text)
                fetched_status = response.xpath('//a:Estado', namespaces=namespace)
                status = fetched_status[0] if fetched_status else ''
            except Exception as e:
                move.message_post(body=_("Failure during update of the SAT status: %(msg)s", msg=str(e)))
                continue

            if status == 'Vigente':
                move.l10n_mx_edi_sat_status = 'valid'
            elif status == 'Cancelado':
                move.l10n_mx_edi_sat_status = 'cancelled'
            elif status == 'No Encontrado':
                move.l10n_mx_edi_sat_status = 'not_found'
            else:
                move.l10n_mx_edi_sat_status = 'none'

