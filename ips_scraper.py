import requests

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
            print("Conexion rechazada por el servidor. Tiempo de espera, 60s")
            time.sleep(60)
            print("Fin tiempo de espera")
            continue

    return response

def main():
    pass
