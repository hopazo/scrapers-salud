import requests
import time

from bs4 import BeautifulSoup
from random import randint


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
