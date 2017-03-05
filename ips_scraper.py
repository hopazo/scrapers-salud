import requests

from bs4 import BeautifulSoup
from random import randint
from time import sleep

sleep(randint(10,100))
CONDICION_DE_VENTA = 'ctl00$ContentPlaceHolder1$chkTipoBusqueda$5'
VENTA_DIRECTA = 'Directa'
MAX_RETRY = 3

#URL Base
base_url = 'http://registrosanitario.ispch.gob.cl/'

def send_request(url, cookie_jar, data=None):
    if data is None: data = {}
    response = ''
    while not response:
        try:
            session = requests.Session()
            if not cookie_jar:
                session.get(url)
                cookie_jar = session.cookies.get_dict()

            request = requests.Request('POST', url, data=data, cookies=cookie_jar)
            response = session.send(request.prepare())
        except:
            print("Conexion rechazada por el servidor.")
            sleep(randint(1,60))
            print("Reintentando")
            continue
    return response, cookie_jar


def init_request_body(dom):
    ctl00 = dom.find(id='ctl00_ContentPlaceHolder1_ScriptManager1_HiddenField')
    __EVENTTARGET = dom.find(id='__EVENTTARGET')
    __EVENTARGUMENT = dom.find(id='__EVENTARGUMENT')
    __LASTFOCUS = dom.find(id='__LASTFOCUS')
    __VIEWSTATE = dom.find(id='__VIEWSTATE')
    __VIEWSTATEGENERATOR = dom.find(id='__VIEWSTATEGENERATOR')
    __VIEWSTATEENCRYPTED = dom.find(id='__VIEWSTATEENCRYPTED')
    __PREVIOUSPAGE = dom.find(id='__PREVIOUSPAGE')
    __EVENTVALIDATION = dom.find(id='__EVENTVALIDATION')

    request_body = {
        'ctl00_ContentPlaceHolder1_ScriptManager1_HiddenField': ctl00,
        '__EVENTTARGET': __EVENTTARGET,
        '__EVENTARGUMENT': __EVENTARGUMENT,
        '__LASTFOCUS': __LASTFOCUS,
        '__VIEWSTATE': __VIEWSTATE,
        '__VIEWSTATEGENERATOR': __VIEWSTATEGENERATOR,
        '__VIEWSTATEENCRYPTED': __VIEWSTATEENCRYPTED,
        '__EVENTVALIDATION': __EVENTVALIDATION
    }

    if __PREVIOUSPAGE != '':
        request_body['__PREVIOUSPAGE'] = __PREVIOUSPAGE
    return request_body


def set_form_options(request_body, option, value):
    request_body[option] = value
    if option == CONDICION_DE_VENTA:
        request_body[CONDICION_DE_VENTA] = 'on'


def main():
    response, cookie_jar = send_request(base_url)
    if not response:
        print("El servidor no responde")
        return
    request_body = init_request_body(response)
    request_body = set_form_options(request_body, CONDICION_DE_VENTA, VENTA_DIRECTA)
