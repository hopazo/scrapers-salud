import argparse
import enum
import threading

from datetime import date, datetime
from math import ceil, floor
from PageParser import PageParser
from ThreadPool import ThreadPool

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
    referencia_tramite = 'ctl00_ContentPlaceHolder1_lblRefTramite'
    equivalencia_terapeutica = 'ctl00_ContentPlaceHolder1_lblEquivalencia'
    titular = 'ctl00_ContentPlaceHolder1_lblEmpresa'
    estado_registro = 'ctl00_ContentPlaceHolder1_lblEstado'
    resolucion_inscripcion = 'ctl00_ContentPlaceHolder1_lblResInscribase'
    fecha_inscripcion = 'ctl00_ContentPlaceHolder1_lblFchInscribase'
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


class FichaProductoParser(PageParser):
    def __init__(self, product_id):
        PageParser.__init__(self, url=url_ficha + product_id)
        self.product_id = product_id

    def product(self):
        self._request()
        product_data = self._get_product_description()
        # product['packing'] = self._get_packaging()
        # product['companies'] = self._get_companies()
        product_data['registro'] = self.product_id
        product_data['formula'] = self._get_formula()
        return product_data

    def _get_product_description(self):
        description = {}
        for k in FichaProducto:
            node = self.dom.find(id=k.value)
            if not node or not node.string:
                description[k.name] = None
            elif k.name in ['fecha_inscripcion', 'ultima_renovacion', 'proxima_renovacion']:
                description[k.name] = datetime.strptime(node.string.strip(), "%d/%m/%Y").date().strftime('%Y-%m-%d')
            else:
                description[k.name] = node.string.strip().lower()
        return description

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
                'unidad_medida': td[2].find('span').string,
                'parte': td[3].find('span').string,
                'vigente': None
            }
            formulas.append(formula)
        return formulas


class IspParser(PageParser, threading.Thread):
    # Cantidad máxima de resultados por página
    RESULTS_PER_PAGE = 25
    # Cantidad máxima de links a páginas de resultados mostradas simultaneamente
    MAX_PAGES = 10
    thread_data = threading.local()

    def __init__(self, sale_terms, status, page_number=1, max_retry=3, max_wait_timeout=10, tasks=None):
        threading.Thread.__init__(self)
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
            try:
                del self.request_body[Placeholders.buscar.value]
            except KeyError:
                pass
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
        self._update_request_body()

    def go_to_page(self, page_number):
        # Avanzar entre las páginas de resultados en intervalos de MAX_PAGES, hasta encontrar link con la página buscada
        skip_times = int(floor(page_number/self.MAX_PAGES)) + 1
        for i in range(1, skip_times):
            page_arg = 'Page$' + str(i * self.MAX_PAGES + 1)
            self._set_form_param(Placeholders.datos_busqueda, page_arg)
            self._request()
            self._update_request_body()
        page_arg = 'Page$' + str(page_number)
        self._set_form_param(Placeholders.datos_busqueda, page_arg)
        self._request()
        self._update_request_body()

    @property
    def pages_count(self):
        self._connect()
        total = self.dom.find(id='ctl00_ContentPlaceHolder1_lblCantidadEC').string
        count = ceil(int(total)/self.RESULTS_PER_PAGE)
        return int(count)

    def _process_page(self):
        first_register = True
        # Obtiene todas las filas de la tabla
        trs = self.dom.find(id='ctl00_ContentPlaceHolder1_gvDatosBusqueda').find_all('tr')
        today = date.today()
        for tr in trs:
            tds = tr.find_all('td', class_='tdsimple')
            if len(tds) != 7:
                continue
            registro = tds[1].text.strip()
            if first_register:
                print('{0} procesando página {1}, desde registro {2}'.format(self.name, self.page_number, registro))
                first_register = False
            parser = FichaProductoParser(product_id=registro)
            product = parser.product()
            product['fecha_descarga'] = today.strftime('%Y-%m-%d')
            product['vigente'] = self.status.value
            self.append_record(product)


    def append_record(self, record):
        """
        Almacena un medicamento en un archivo json
        :param record: Diccionario que contiene los datos del medicamento
        :return:
        """
        f = 'meds-{0}-{1}-{2}-{3}.json'.format(self.page_number, self.sale_terms.name, self.status.name, date.today().strftime('%Y-%m-%d'))
        with open(f, 'a') as f:
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
            try:
                self._connect()
                if self.page_number != 1:
                    self.go_to_page(self.page_number)
                self._process_page()
                print('Página {0} completada por {1}...'.format(self.page_number, self.name))
            except AttributeError as e:
                print(str(e))
            except Exception as e:
                print(str(e))
            finally:
                self.tasks.task_done()


def main(condicion_venta, estado, threads):
    start = datetime.now()
    try:
        condicion_venta = condicion_venta.replace('-', '_')
        estado = estado.replace('-', '_')
        condicion_venta = CondicionVenta[condicion_venta]
        estado = Estado[estado]
        max_threads = int(threads)
        print('Parámetros de búsqueda')
        print('Venta : {0}'.format(condicion_venta.value))
        print('Vigente: {0}'.format(estado.value))
    except KeyError:
        print('No fue posible determinar la condicion de venta o estado de medicamentos a procesar')
        return 1
    except ValueError:
        print('No se proporcionó un número de hilos de ejecución válido')
        return 1

    thread = IspParser(sale_terms=condicion_venta, status=estado)
    max_pages = thread.pages_count

    pool = ThreadPool(max_threads, IspParser)
    for i in range(1, max_pages + 1):
        pool.add_task({'sale_terms': condicion_venta, 'status': estado, 'page_number': i})
    pool.wait_completion()
    end = datetime.now()
    print('Tiempo transcurrido: {0}'.format(end - start))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Descargar medicamentos desde la web del registro sanitario de ISPCh')
    parser.add_argument('--venta', help='Condición de venta de los medicamentos [directa|receta-medica|receta-retenida|receta-cheque]', default='directa')
    parser.add_argument('--estado', help='Vigencia de los medicamentos [vigente|no-vigente|suspendido]', default='vigente')
    parser.add_argument('--threads', help='Cantidad máxima de hilos de ejecución', type=int, default='4')
    args = parser.parse_args()
    main(args.venta, args.estado, args.threads)
