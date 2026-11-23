"""Desktop client for opt-in Spiderpot activity email."""

import json
import os
from threading import Lock, Thread
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from spiderpot_support import crypt, resource


class MailError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def configured_url():
    if url := os.environ.get('SPIDERPOT_MAIL_URL'):
        return url
    try:
        return resource('store/mail-url.txt').read_text(encoding='utf-8').strip()
    except OSError:
        return ''


class MailClient:
    def __init__(self, url):
        try:
            address = urlsplit(url)
            secure = address.scheme == 'https' or (address.scheme == 'http' and address.hostname == '127.0.0.1')
            if not secure or not address.hostname or address.username is not None or address.query or address.fragment:
                raise ValueError
        except ValueError:
            raise MailError('E-posta servisi için geçerli bir HTTPS adresi gerekiyor.') from None
        self.url = url.rstrip('/')
        self.opener = build_opener(NoRedirect())

    def post(self, action, body, *, token=None):
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if token is not None:
            headers['Authorization'] = f'Bearer {token}'
        request = Request(f'{self.url}/v1/{action}', json.dumps(body).encode('utf-8'), headers)
        try:
            with self.opener.open(request, timeout=12) as response:
                return json.loads(response.read(4096))
        except HTTPError as error:
            messages = {400: 'E-posta adresini veya doğrulama kodunu kontrol edin.',
                        401: 'E-posta adresini yeniden doğrulayın.',
                        429: 'Yeni kod istemeden önce biraz bekleyin.'}
            error.close()
            raise MailError(messages.get(error.code, 'E-posta servisi şu anda kullanılamıyor.')) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise MailError('E-posta servisine bağlanılamadı.') from None

    def request_code(self, email):
        return self.response_field(self.post('request', {'email': email.strip()}), 'challenge')

    def confirm(self, challenge, code):
        return self.response_field(self.post('confirm', {'challenge': challenge, 'code': code.strip()}), 'token')

    def alert(self, token):
        reply = self.post('alert', {}, token=token)
        if not isinstance(reply, dict) or type(reply.get('sent')) is not bool:
            raise MailError('Servis gönderim sonucunu doğrulamadı.')
        return reply['sent']

    @staticmethod
    def response_field(reply, key):
        if not isinstance(reply, dict) or not isinstance(reply.get(key), str) or not reply[key]:
            raise MailError('E-posta servisi geçersiz bir yanıt verdi.')
        return reply[key]


def encode_enrollment(enrollment):
    return crypt(json.dumps(enrollment).encode('utf-8')).hex() if enrollment else ''


def decode_enrollment(encrypted):
    if encrypted:
        try:
            values = json.loads(crypt(bytes.fromhex(encrypted), decrypt=True))
            if isinstance(values, dict) and all(isinstance(values.get(key), str) and values[key]
                                               for key in ('url', 'email', 'token')):
                return values
        except (OSError, ValueError, TypeError):
            pass
    return None


class ActivityMailer:
    def __init__(self, enrollment, on_error):
        self.client = MailClient(enrollment['url'])
        self.token = enrollment['token']
        self.on_error = on_error
        self.lock = Lock()
        self.generation = None

    def send_once(self, generation, on_result):
        with self.lock:
            if self.generation is not None and generation <= self.generation:
                return
            self.generation = generation
        Thread(target=self.send, args=(on_result,), daemon=True).start()

    def send(self, on_result):
        try:
            sent = self.client.alert(self.token)
        except MailError as error:
            on_result('E-posta gönderilemedi')
            self.on_error(str(error))
        else:
            on_result('E-posta gönderildi' if sent else 'E-posta gönderim sınırına ulaşıldı')
