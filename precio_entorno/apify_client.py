import json
import re
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApifyClient:
    def __init__(self, token=None):
        self.token = token

    def request(self, path, *, params=None, payload=None):
        query = '?' + urlencode(params) if params else ''
        headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
        data = None
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(payload).encode()
        request = Request(f'https://api.apify.com/v2/{path}{query}', headers=headers, data=data)
        try:
            with urlopen(request, timeout=40) as response:
                return json.load(response)
        except HTTPError as error:
            raise RuntimeError(f'Apify respondió HTTP {error.code}.') from None
        except (URLError, TimeoutError):
            raise RuntimeError('No se pudo completar la solicitud a Apify.') from None

    def wait(self, run_id, max_seconds=360):
        if not re.fullmatch(r'[A-Za-z0-9]+', run_id):
            raise ValueError('ID de corrida inválido.')
        deadline = monotonic() + max_seconds
        while monotonic() < deadline:
            run = self.request(f'actor-runs/{run_id}', params={'waitForFinish': 20})['data']
            if run['status'] in {'SUCCEEDED', 'FAILED', 'TIMED-OUT', 'ABORTED'}:
                sleep(10)  # El costo informado al terminar puede ser preliminar.
                return self.request(f'actor-runs/{run_id}')['data']
            sleep(1)
        raise RuntimeError(f'La corrida {run_id} sigue pendiente. Revisala en Apify Console.')

