# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from zeep import Client
from zeep.transports import Transport

credentials = {
    'username': 'cfdi@vauxoo.com', 'password': 'vAux00__', 
    'sign_url': 'http://demo-facturacion.finkok.com/servicios/soap/stamp.wsdl', 
    'cancel_url': 'http://demo-facturacion.finkok.com/servicios/soap/cancel.wsdl'
}

transport = Transport(timeout=20)
client = Client(credentials['cancel_url'], transport=transport)

UUIDS_list = client.get_type("ns0:UUIDArray")()
UUIDS_list.UUID.append({
    "UUID": "DEED0A09-9102-4106-BF1B-14172FF34E12", 
    "FolioSustitucion": "",
    "Motivo": "02"
})
print('--- UUIDS_list', UUIDS_list)
"""
invoices_obj = client.get_type('ns0:UUID')
invoices_obj._UUID = 'DEED0A09-9102-4106-BF1B-14172FF34E12'
invoices_obj._FolioSustitucion = ''
invoices_obj._Motivo = '02'
UUIDS_list = client.get_type('ns0:UUIDArray')
UUIDS_list( [ invoices_obj ] )
"""