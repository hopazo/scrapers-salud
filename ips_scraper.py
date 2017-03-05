import requests

from random import randint
from time import sleep

sleep(randint(10,100))
MAX_RETRY = 3
#URL Base
base_url = 'http://registrosanitario.ispch.gob.cl/'

def connect(url, cookie_jar, data=None):
    if data is None: data = {}
    response = ''
    while len(response) == 0:
        try:
            session = requests.Session()
            if not cookie_jar:
                session.get(url)
                cookie_jar = session.cookies.get_dict()

            request = requests.Request('POST', url, data=data, cookies=cookie_jar)
            prepped = request.prepare()  # Prepara el request
            response = session.send(prepped)
        except:
            print("Conexion rechazada por el servidor.")
            sleep(randint(1,60))
            print("Reintentando")
            continue

    return response

def main():
    pass
