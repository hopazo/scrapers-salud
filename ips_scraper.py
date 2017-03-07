import enum
import requests

from bs4 import BeautifulSoup
from random import randint
from queue import Queue
from threading import Thread
from time import sleep

base_url = 'http://registrosanitario.ispch.gob.cl/'
url_ficha = 'http://registrosanitario.ispch.gob.cl/Ficha.aspx?RegistroISP='

class TipoBusqueda(enum.Enum):
    condicion_venta = 'ctl00$ContentPlaceHolder1$chkTipoBusqueda$5'


class Placeholders(enum.Enum):
    condicion = 'ctl00$ContentPlaceHolder1$ddlCondicion'
    estado = 'ctl00$ContentPlaceHolder1$ddlEstado'
    datos_busqueda = 'ctl00$ContentPlaceHolder1$gvDatosBusqueda'
    buscar = 'ctl00$ContentPlaceHolder1$btnBuscar'
    nombre = 'ctl00_ContentPlaceHolder1_lblNombre'
    ref_tramite = 'ctl00_ContentPlaceHolder1_lblRefTramite'
    bioequivalencia = 'ctl00_ContentPlaceHolder1_lblEquivalencia'
    empresa = 'ctl00_ContentPlaceHolder1_lblEmpresa'
    titular = 'ctl00_ContentPlaceHolder1_lblEstado'
    resolution = 'ctl00_ContentPlaceHolder1_lblResInscribase'
    date_signed = 'ctl00_ContentPlaceHolder1_lblFchInscribase'
    last_renovation = 'ctl00_ContentPlaceHolder1_lblFchResolucion'
    next_renewal_date = 'ctl00_ContentPlaceHolder1_lblProxRenovacion'
    regime = 'ctl00_ContentPlaceHolder1_lblRegimen'
    via_administration = 'ctl00_ContentPlaceHolder1_lblViaAdministracion'
    sale_condition = 'ctl00_ContentPlaceHolder1_lblCondicionVenta'
    expend_type = 'ctl00_ContentPlaceHolder1_lblExpende'
    indication = 'ctl00_ContentPlaceHolder1_lblIndicacion'

class CondicionVenta(enum.Enum):
    directa = 'Directa'
    receta_medica = 'Receta Médica'
    receta_retenida = 'Receta Médica Retenida'
    receta_cheque = 'Receta Cheque'


class Estado(enum.Enum):
    vigente = 'Sí'
    no_vigente = 'No'
    suspendido = 'Suspendido'


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


class IspParser(Thread):
    def __init__(self, sale_terms, status, page_number=1, max_retry=3, tasks=None):
        Thread.__init__(self)
        self.daemon = True
        self.sale_terms = sale_terms
        self.status = status
        self.page_number = page_number
        self.cookie_jar = None
        self.request_body = {}
        self.max_retry = max_retry
        self.current_page = None
        self.dom = None
        self.url = base_url
        self.tasks = tasks

    @classmethod
    def from_queue(cls, tasks):
        thread = cls(sale_terms=None, status=None, page_number=None, tasks=tasks)
        thread.start()
        return thread

    def _request(self):
        self.current_page = None
        self.dom = None
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
        self.dom = BeautifulSoup(self.current_page.content, 'lxml')

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

        # Obtener valores necesarios para enviar el formulario
        self._update_request_body()

        # Marcar checkboxes con opciones de búsqueda
        self._set_form_option(TipoBusqueda.condicion_venta)

        # Obtener el DOM actualizado con las opciones de búsqueda marcadas
        self._request()

        # Obtener los nuevos campos del formulario
        self._update_request_body()

        # Completar campos con los parámetros de búsqueda
        self._set_form_param(Placeholders.estado, self.status)
        self._set_form_param(Placeholders.condicion, self.sale_terms)
        self.request_body[Placeholders.buscar.value] = 'Buscar'

        # Enviar la petición y obtener el DOM con los resultados
        self._request()

    def go_to_page(self, page_number):
        # Cambiar página
        page_number = 'Page$' + str(page_number)
        self._set_form_param(Placeholders.datos_busqueda, page_number)
        self._request()

    @property
    def pages_count(self):
        self._connect()
        table = self.dom.find(id='ctl00_ContentPlaceHolder1_gvDatosBusqueda')
        pagination_footer = table.find('td', attrs={'colspan': 7})
        count = len(pagination_footer.find_all('td')) if pagination_footer else 1
        return count

    def _process_page(self):
        # Obtiene todas las filas de la tabla
        trs = self.dom.find(id='ctl00_ContentPlaceHolder1_gvDatosBusqueda').find_all('tr')
        for tr in trs:
            tds = tr.find_all('td', class_='tdsimple')
            if len(tds) != 7:
                continue
            registro = tds[1].text.strip()
            empresa = tds[4].text.strip()
            principio_activo = tds[5].text.strip()
            control_legal = tds[6].text.strip()

            self.cookie_jar = None
            self.request_body = None
            self.url = url_ficha + registro
            self._request()
            self._get_product_description()

    def _get_product_description(self):
        name = self.dom.find(id=Placeholders.nombre.value).string
        ref = self.dom.find(id=Placeholders.ref_tramite.value).string
        therapeutic_equivalence = self.dom.find(id=Placeholders.bioequivalencia.value).string
        holder = self.dom.find(id=Placeholders.empresa.value).string
        record_status = self.dom.find(id=Placeholders.titular.value).string
        resolution = self.dom.find(id=Placeholders.resolution.value).string
        date_signed = self.dom.find(id=Placeholders.date_signed.value).string
        last_renovation = self.dom.find(id=Placeholders.last_renovation.value).string
        next_renewal_date = self.dom.find(id=Placeholders.next_renewal_date.value).string
        regime = self.dom.find(id=Placeholders.regime.value).string
        via_administration = self.dom.find(id=Placeholders.via_administration.value).string
        sale_condition = self.dom.find(id=Placeholders.sale_condition.value).string
        expend_type = self.dom.find(id=Placeholders.expend_type.value).string
        indication = self.dom.find(id=Placeholders.indication.value)

    def run(self):
        while True:
            task = self.tasks.get()
            self.page_number = task['page_number']
            self.sale_terms = task['sale_terms']
            self.status = task['status']
            self.current_page = None
            self.cookie_jar = None
            self.request_body = {}
            print('Procesando pagina (%s)...' % self.page_number)
            self._connect()
            if self.page_number != 1:
                self.go_to_page(self.page_number)
            self._process_page()
            print('Pagina (%s) completada' % self.page_number)
            self.tasks.task_done()


def main():
    max_threads = 1
    thread = IspParser(sale_terms=CondicionVenta.receta_cheque, status=Estado.vigente)
    max_pages = thread.pages_count

    pool = ThreadPool(max_threads)
    for i in range(1, max_pages + 1):
        pool.add_task({'sale_terms': CondicionVenta.receta_cheque, 'status': Estado.vigente, 'page_number': i})
    pool.wait_completion()
