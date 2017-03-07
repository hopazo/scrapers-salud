import enum
import requests

from bs4 import BeautifulSoup
from random import randint
from queue import Queue
from threading import Thread
from time import sleep

# URL Base
base_url = 'http://registrosanitario.ispch.gob.cl/'


class TipoBusqueda(enum.Enum):
    condicion_venta = 'ctl00$ContentPlaceHolder1$chkTipoBusqueda$5'


class Placeholders(enum.Enum):
    condicion = 'ctl00$ContentPlaceHolder1$ddlCondicion'
    estado = 'ctl00$ContentPlaceHolder1$ddlEstado'
    datos_busqueda = 'ctl00$ContentPlaceHolder1$gvDatosBusqueda'
    buscar = 'ctl00$ContentPlaceHolder1$btnBuscar'


class CondicionVenta(enum.Enum):
    directa = 'Directa'
    receta_medica = 'Receta Médica'
    receta_retenida = 'Receta Médica Retenida'
    receta_cheque = 'Receta Cheque'


class Estado(enum.Enum):
    vigente = 'Sí'
    no_vigente = 'No'
    suspendido = 'Suspendido'


class IspParser(Thread):
    def __init__(self, sale_terms, status, page_number=1, max_retry=3, tasks=None):
        Thread.__init__(self)
        self.sale_terms = sale_terms
        self.status = status
        self.page_number = page_number
        self.cookie_jar = None
        self.request_body = {}
        self.max_retry = max_retry
        self.current_page = None
        self.dom = None
        self.url = 'http://registrosanitario.ispch.gob.cl/'
        self.tasks = tasks

    @classmethod
    def from_queue(cls, tasks):
        thread = cls(sale_terms=None, status=None, page_number=None, tasks=tasks)
        thread.start()
        return thread

    def _request(self):
        self.current_page = ''
        last_exception = None
        i = 1
        while not self.current_page and i < self.max_retry:
            try:
                session = requests.Session()
                if not self.cookie_jar:
                    session.get(self.url)
                    self.cookie_jar = session.cookies.get_dict()

                request = requests.Request('POST', self.url, data=self.request_body, cookies=self.cookie_jar)
                self.current_page = session.send(request.prepare())
            except requests.exceptions.RequestException as e:
                last_exception = e
                sleep(randint(1, 60))
                continue
            i += 1
        if not self.current_page:
            raise last_exception

    def _set_form_option(self, option):
        if option == TipoBusqueda.condicion_venta:
            self.request_body['__EVENTTARGET'] = option.value
            self.request_body[TipoBusqueda.condicion_venta.value] = 'on'
        else:
            self.request_body['__EVENTTARGET'] = ''

    def _set_form_param(self, option, param):
        if option == Placeholders.estado:
            self.request_body[Placeholders.estado.value] = param.value
        elif option == Placeholders.condicion:
            self.request_body[Placeholders.condicion.value] = param.value
        elif option == Placeholders.datos_busqueda:
            self.request_body['__EVENTTARGET'] = Placeholders.datos_busqueda.value
            self.request_body['__EVENTARGUMENT'] = param
        else:
            self.request_body['__EVENTARGUMENT'] = param.value

    def _update_request_body(self):
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
        new_body = {key: self.dom.find(id=key)['value'] if self.dom.find(id=key) else '' for key in args}
        previous_page = self.dom.find(id='__PREVIOUSPAGE')
        if previous_page:
            new_body['__PREVIOUSPAGE'] = previous_page
        self.request_body.update((k, new_body[k]) for k in new_body.keys())

    def _connect(self):
        # Acceder a la url base y obtener el DOM
        self._request()
        self.dom = BeautifulSoup(self.current_page.content, 'lxml')

        # Obtener valores necesarios para enviar el formulario
        self._update_request_body()

        # Marcar checkboxes con opciones de búsqueda
        self._set_form_option(TipoBusqueda.condicion_venta)

        # Obtener el DOM actualizado con las opciones de búsqueda marcadas
        self._request()
        self.dom = BeautifulSoup(self.current_page.content, 'lxml')

        # Obtener los nuevos campos del formulario
        self._update_request_body()

        # Completar campos con los parámetros de búsqueda
        self._set_form_param(Placeholders.estado, Estado.no_vigente)
        self._set_form_param(Placeholders.condicion, CondicionVenta.receta_cheque)
        self.request_body[Placeholders.buscar.value] = 'Buscar'

        # Enviar la petición y obtener el DOM con los resultados
        self._request()
        self.dom = BeautifulSoup(self.current_page.content, 'lxml')

    def go_to_page(self, page_number):
        # Cambiar página
        page_number = 'Page$' + str(page_number)
        self._set_form_param(Placeholders.datos_busqueda, page_number)
        self._request()
        self.dom = BeautifulSoup(self.current_page.content, 'lxml')

    @property
    def pages_count(self):
        self._connect()
        pagination_footer = self.dom.find(id='ctl00_ContentPlaceHolder1_gvDatosBusqueda').find('td', attrs={'colspan': 7})
        count = len(pagination_footer.find_all('td')) if pagination_footer else 1
        return count

    def process_page(self):
        sleep(2)
        pass

    def run(self):
        while True:
            task = self.tasks.get()
            self.page_number = task['page_number']
            self.sale_terms = task['sale_terms']
            self.status = task['status']
            print('Running page (%s)...this may take several minutes. Please be patient' % self.page_number)
            self._connect()
            if self.page_number != 1:
                self.go_to_page(self.page_number)
            self.process_page()
            print('Complete (%s)' % self.page_number)
            if self.tasks:
                self.tasks.task_done()
            return


def main():
    max_threads = 4
    thread = IspParser(sale_terms=CondicionVenta.receta_cheque, status=Estado.vigente)
    max_pages = thread.pages_count

    pool = ThreadPool(max_threads)
    for i in range(2, max_pages):
        pool.add_task({'sale_terms': CondicionVenta.receta_cheque, 'status': Estado.vigente, 'page_number': i})
    pool.wait_completion()


class ThreadPool:
    """ Pool of threads consuming tasks from a queue """
    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            IspParser.from_queue(tasks=self.tasks)

    def add_task(self, task):
        """ Add a task to the queue """
        self.tasks.put(task)

    def wait_completion(self):
        """ Wait for completion of all the tasks in the queue """
        self.tasks.join()
