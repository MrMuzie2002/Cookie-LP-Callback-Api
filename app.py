from enum import Enum
from flask import Flask, jsonify, request
from time import time

try:
    import vk_api
except ImportError:
    import os

    os.system("pip3.8 install --user vk_api")
finally:
    import vk_api
    from vk_api.longpoll import VkLongPoll
    from vk_api.exceptions import ApiError, AuthError, Captcha

######################################################################################################

VK_TOKEN = ''
# Токен VK API, полученный по инструкции из статьи.

SECRET_KEY = ''
# Секретный ключ для идентификации запросов, который вы указали боту.

DISALLOWED_METHODS = [
]
# Если оставить как есть, будет выдано разрешение на использование всех методов, что рекомендуется.

######################################################################################################

app = Flask(__name__)


class CookieCallback:
    class ErrorCode(Enum):
        System = 1
        Api = 2
        IncorrectKey = 3
        MethodNotAllowed = 4
        AuthError = 5
        CaptchaError = 6

    def __init__(self):
        self.api = vk_api.VkApi(token=VK_TOKEN, api_version='5.135')
        self.longpoll = VkLongPoll(self.api, mode=2)
        self._last_lp_connect = 0

        app.add_url_rule('/test', 'test_handler', self.test_handler, methods=['POST'])
        app.add_url_rule('/api', 'api_handler', self.api_handler, methods=['POST'])
        app.add_url_rule('/longpoll', 'longpoll_handler', self.longpoll_handler, methods=['POST'])
        app.add_url_rule('/event', 'event_handler', self.event_handler, methods=['POST'])

    def _get_events(self):
        try:
            if time() - self._last_lp_connect > 10:
                self.longpoll.update_longpoll_server()
            self._last_lp_connect = time()
            return [event.raw for event in self.longpoll.check()]
        except Exception:
            self.longpoll.update_longpoll_server()
            return []

    def test_handler(self):
        try:
            if request.json['secret_key'] == SECRET_KEY:
                return 'ok'
            else:
                return 'che'
        except Exception:
            return 'che'

    def longpoll_handler(self):
        try:
            if request.json['secret_key'] == SECRET_KEY:
                return jsonify({
                    'success': 1,
                    'updates': self._get_events()
                })
            else:
                return jsonify({
                    'success': 0,
                    'err_msg': 'Incorrect secret key.',
                    'err_code': self.ErrorCode.IncorrectKey.value
                })
        except Exception:
            return jsonify({
                'success': 0,
                'err_msg': 'Server error.',
                'err_code': self.ErrorCode.System.value
            })

    def api_handler(self):
        try:
            if request.json['secret_key'] != SECRET_KEY:
                return jsonify({
                    'success': 0,
                    'err_msg': 'Incorrect secret key.',
                    'err_code': self.ErrorCode.IncorrectKey.value
                })
            if request.json['method'] in DISALLOWED_METHODS:
                return jsonify({
                    'success': 0,
                    'err_msg': 'Method not allowed.',
                    'err_code': self.ErrorCode.MethodNotAllowed.value
                })

            response = self.api.method(
                method=request.json['method'], values=request.json['args']
            )
            return jsonify({
                'success': 1,
                'response': response
            })

        except Captcha:
            return jsonify({
                'success': 0,
                'err_msg': 'Captcha error.',
                'err_code': self.ErrorCode.CaptchaError.value,
            })
        except AuthError:
            return jsonify({
                'success': 0,
                'err_msg': 'Auth error.',
                'err_code': self.ErrorCode.AuthError.value,
            })
        except ApiError as err:
            return jsonify({
                'success': 0,
                'err_msg': str(err),
                'err_code': self.ErrorCode.Api.value,
                'err_data': err.error
            })
        except Exception:
            return jsonify({
                'success': 0,
                'err_msg': 'Server error.',
                'err_code': self.ErrorCode.System.value,
            })

    def event_handler(self):
        pass


CookieCallback()