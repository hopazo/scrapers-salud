import enum
import requests

from bs4 import BeautifulSoup
from random import randint
from time import sleep

MAX_RETRY = 3

# URL Base
base_url = 'http://registrosanitario.ispch.gob.cl/'


class TipoBusqueda(enum.Enum):
    condicion_venta = 'ctl00$ContentPlaceHolder1$chkTipoBusqueda$5'


class Placeholders(enum.Enum):
    condicion = 'ctl00$ContentPlaceHolder1$ddlCondicion'
    estado = 'ctl00$ContentPlaceHolder1$ddlEstado'


class CondicionVenta(enum.Enum):
    directa = 'Directa'
    receta_medica = 'Receta Médica'
    receta_retenida = 'Receta Médica Retenida'
    receta_cheque = 'Receta Cheque'


class Estado(enum.Enum):
    vigente = 'Si'
    no_vigente = 'No'
    suspendido = 'Suspendido'


def send_request(url, cookie_jar=None, data=None):
    if data is None:
        data = {}
    response = ''
    i = 1
    while not response and i < MAX_RETRY:
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
        i += 1
    return response, cookie_jar


def init_request_body(dom, request_body=None):
    if not request_body:
        request_body = {}
        
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
    new_body = {key: dom.find(id=key)['value'] if dom.find(id=key) else '' for key in args}
    previous_page = dom.find(id='__PREVIOUSPAGE')
    if previous_page:
        new_body['__PREVIOUSPAGE'] = previous_page
    request_body.update((k, new_body[k]) for k in new_body.keys())
    return request_body


def set_form_option(request_body, option):
    if option == TipoBusqueda.condicion_venta:
        request_body['__EVENTTARGET'] = option.value
        request_body[TipoBusqueda.condicion_venta.value] = 'on'
    else:
        request_body['__EVENTTARGET'] = ''

    return request_body


def set_form_param(request_body, option, param):
    if option == Placeholders.estado:
        request_body[Placeholders.estado.value] = param.value
    elif option == Placeholders.condicion:
        request_body[Placeholders.condicion.value] = param.value
    else:
        request_body['__EVENTARGUMENT'] = param.value
    return request_body


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
    request_body = set_form_option(request_body, TipoBusqueda.condicion_venta)

    # Obtener el DOM actualizado con las opciones de búsqueda marcadas
    response, cookie_jar = send_request(base_url, cookie_jar=cookie_jar, data=request_body)
    dom2 = BeautifulSoup(response.content, 'lxml')

    # Obtener los nuevos campos del formulario
    request_body = init_request_body(dom2)

    # Completar campos con los parámetros de búsqueda
    request_body = set_form_param(request_body, Placeholders.estado, Estado.suspendido)
    request_body = set_form_param(request_body, Placeholders.condicion, CondicionVenta.receta_cheque)
    request_body['ctl00$ContentPlaceHolder1$btnBuscar'] = 'Buscar'

    # Enviar la petición y obtener el DOM con los resultados
    response, cookie_jar = send_request(base_url, cookie_jar=cookie_jar, data=request_body)
    dom3 = BeautifulSoup(response.content, 'lxml')
