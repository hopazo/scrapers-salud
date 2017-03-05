import requests

from bs4 import BeautifulSoup
from random import randint
from time import sleep

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


def main():
    response, cookie_jar = send_request(base_url)
    if not response:
        print("El servidor no responde")
        return
