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


def send_request(url, cookie_jar=None, data=None):
    if data is None:
        data = {}
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
    args = [
        'ctl00_ContentPlaceHolder1_ScriptManager1_HiddenField',
        '__EVENTTARGET',
        '__EVENTARGUMENT',
        '__LASTFOCUS',
        '__VIEWSTATE',
        '__VIEWSTATEGENERATOR',
        '__VIEWSTATEENCRYPTED',
        '__EVENTVALIDATION',
    ]
    request_body = {key: dom.find(id=key) if dom.find(id=key) else '' for key in args}

    previous_page = dom.find(id='__PREVIOUSPAGE')
    if previous_page:
        request_body['__PREVIOUSPAGE'] = previous_page
    return request_body


def set_form_options(request_body, option, value):
    request_body[option] = value
    if option == CONDICION_DE_VENTA:
        request_body[CONDICION_DE_VENTA] = 'on'


def main():
    # Acceder a la url base y obtener el DOM
    response, cookie_jar = send_request(base_url)
    if not response:
        print("El servidor no responde")
        return
    dom = BeautifulSoup(response.content, 'lxml')

    # Obtener valores necesarios para enviar el formulario
    request_body = init_request_body(dom)

    # Marcar checkboxes con opciones de búsqueda
    form_data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$chkTipoBusqueda$5'
    form_data['ctl00$ContentPlaceHolder1$chkTipoBusqueda$5'] = 'on'
    form_data['ctl00$ContentPlaceHolder1$ddlEstado'] = 'Suspendido'

    # Obtener el DOM actualizado con las opciones de búsqueda marcadas
    response, cookie_jar = send_request(base_url, cookie_jar=cookie_jar, data=request_body)
    dom = BeautifulSoup(response.content, 'lxml')

    # Obtener los nuevos campos del formulario
    request_body = init_request_body(dom)

    # Completar nuevos campos con los parámetros de búsqueda
    pass

    # Enviar la petición y obtener el DOM con los resultados
    response, cookie_jar = send_request(base_url, cookie_jar=cookie_jar, data=request_body)
    dom = BeautifulSoup(response.content, 'lxml')
