import enum
import requests
import time

from bs4 import BeautifulSoup
from random import randint
from queue import Queue
from threading import Thread

base_url = 'http://registrosanitario.ispch.gob.cl/'
url_ficha = 'http://registrosanitario.ispch.gob.cl/Ficha.aspx?RegistroISP='


class TipoBusqueda(enum.Enum):
    condicion_venta = 'ctl00$ContentPlaceHolder1$chkTipoBusqueda$5'


class Placeholders(enum.Enum):
    condicion = 'ctl00$ContentPlaceHolder1$ddlCondicion'
    estado = 'ctl00$ContentPlaceHolder1$ddlEstado'
    datos_busqueda = 'ctl00$ContentPlaceHolder1$gvDatosBusqueda'
    buscar = 'ctl00$ContentPlaceHolder1$btnBuscar'


class FichaProducto(enum.Enum):
    nombre = 'ctl00_ContentPlaceHolder1_lblNombre'
    ref_tramite = 'ctl00_ContentPlaceHolder1_lblRefTramite'
    equivalencia_terapeutica = 'ctl00_ContentPlaceHolder1_lblEquivalencia'
    titular = 'ctl00_ContentPlaceHolder1_lblEmpresa'
    estado = 'ctl00_ContentPlaceHolder1_lblEstado'
    resolucion = 'ctl00_ContentPlaceHolder1_lblResInscribase'
    fecha_inscribase = 'ctl00_ContentPlaceHolder1_lblFchInscribase'
    ultima_renovacion = 'ctl00_ContentPlaceHolder1_lblFchResolucion'
    proxima_renovacion = 'ctl00_ContentPlaceHolder1_lblProxRenovacion'
    regimen = 'ctl00_ContentPlaceHolder1_lblRegimen'
    via_administracion = 'ctl00_ContentPlaceHolder1_lblViaAdministracion'
    condicion_venta = 'ctl00_ContentPlaceHolder1_lblCondicionVenta'
    tipo_establecimiento = 'ctl00_ContentPlaceHolder1_lblExpende'
    indicacion = 'ctl00_ContentPlaceHolder1_lblIndicacion'


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


class PageParser:
    def __init__(self, url, max_retry=3, max_wait_timeout=10):
        self.url = url
        self.cookie_jar = None
        self.request_body = {}
        self.max_retry = max_retry
        self.current_page = None
        self.dom = None
        self.max_wait_timeout = max_wait_timeout

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
                time.sleep(randint(1, self.max_wait_timeout))
                continue
            i += 1
        if not self.current_page:
            raise last_exception
        self.dom = BeautifulSoup(self.current_page.content, 'lxml')


class FichaProductoParser(PageParser):
    def __init__(self, product_id):
        PageParser.__init__(self, url=url_ficha + product_id)

    def product(self):
        self._request()
        product = self._get_product_description()
        # product['packing'] = self._get_packaging()
        # product['companies'] = self._get_companies()
        product['formula'] = self._get_formula()
        return product

    def _get_product_description(self):
        return {k.name: self.dom.find(id=k.value).string for k in FichaProducto if self.dom.find(id=k.value)}

    def _get_packaging(self):
        """
        Obtener información de envasado de un producto
        :return:
        """
        pass

    def _get_companies(self):
        """
        Obtener información de empresas realacionadas a un producto
        :return:
        """
        pass

    def _get_formula(self):
        """
        Obtener formula (principios activos y concentración), de un producto
        :return:
        """
        formulas = []
        trs = self.dom.find(id='ctl00_ContentPlaceHolder1_gvFormulas').find_all('tr')
        for tr in trs:
            # Se asegura de conseguir las filas que sean de formulas
            td = tr.find_all('td', class_='tdsimple')
            if len(td) != 4:
                continue
            formula = {
                'nombre': td[0].find('span').string,
                'concentracion': td[1].find('span').string,
                'unidad': td[2].find('span').string,
                'parte': td[3].find('span').string
            }
            formulas.append(formula)
        return formulas


class IspParser(PageParser, Thread):
    def __init__(self, sale_terms, status, page_number=1, max_retry=3, max_wait_timeout=10, tasks=None):
        Thread.__init__(self)
        PageParser.__init__(self, base_url, max_retry, max_wait_timeout)
        self.daemon = True
        self.sale_terms = sale_terms
        self.status = status
        self.page_number = page_number
        self.tasks = tasks

    @classmethod
    def from_queue(cls, tasks):
        thread = cls(sale_terms=None, status=None, page_number=None, tasks=tasks)
        thread.start()
        return thread

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
            control_legal = tds[6].text.strip()
            parser = FichaProductoParser(product_id=registro)
            product = parser.product()
            product['control_legal'] = control_legal
            product['titular'] = empresa
            self.append_record(product)

    def append_record(self, record):
        """
        Almacena un medicamento en un archivo json
        :param record: Diccionario que contiene los datos del medicamento
        :return:
        """
        with open('medicines+{0}.json'.format(self.page_number), 'a') as f:
            import json
            json.dump(record, f)
            f.write('\n')

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
            try:
                self._connect()
                if self.page_number != 1:
                    self.go_to_page(self.page_number)
                self._process_page()
                print('Pagina (%s) completada' % self.page_number)
            except Exception as e:
                print(e)
            finally:
                self.tasks.task_done()


def main(condicion_venta, estado, threads):

    try:
        condicion_venta = condicion_venta.replace('-','_')
        estado = estado.replace('-', '_')
        condicion_venta = CondicionVenta[condicion_venta]
        estado = Estado[estado]
        threads = int(threads)
        print('Parámetros de búsqueda')
        print('Venta : {0}'.format(condicion_venta.value))
        print('Vigente: {0}'.format(estado.value))
    except KeyError:
        print('No fue posible determinar la condicion de venta o estado de medicamentos a procesar')
        exit(1)
    except ValueError:
        print('No se proporcionó un número de hilos de ejecución válido')
        exit(1)

    max_threads = threads
    thread = IspParser(sale_terms=condicion_venta, status=estado)
    max_pages = thread.pages_count

    pool = ThreadPool(max_threads)
    for i in range(1, max_pages + 1):
        pool.add_task({'sale_terms': CondicionVenta.receta_cheque, 'status': Estado.vigente, 'page_number': i})
    pool.wait_completion()
