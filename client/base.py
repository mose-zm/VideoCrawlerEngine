
from abc import ABCMeta
from fastapi.routing import APIRoute
import requests
from requests import Session
from urllib.parse import urljoin
from config import get_config
from typing import Sequence, Optional, Type, Any
import sys
import re


def method_not_allowed(*args, **kwargs):
    """ 方法不允许。"""
    raise NotImplementedError('不允许的方法。')


class APIRequestMethod:
    # METHODS = ('post', 'get', 'put', 'delete')
    METHODS = ('post', 'get')

    def __init__(
        self,
        session: Session,
        gateway: str,
        path: str,
        methods: Sequence[str] = (),
        response_model: Optional[Type[Any]] = None,
        description: str = None,
        hook=None,
        doc: str = None,
    ):
        self.session = session
        self.gateway = gateway
        self.api = path
        self.methods = methods
        self.description = description
        self.response_model = response_model
        # 禁用没有对应方法的接口
        [setattr(self, met.lower(), method_not_allowed)
         for met in set(self.METHODS).difference([m.lower() for m in methods])]

    def post(self, **kwargs):
        prepare_headers = {}
        resp = self.session.post(
            url=urljoin(self.gateway, self.api),
            json=kwargs
        )
        res_json = resp.json()
        if self.response_model:
            return self.response_model(**res_json)
        return resp.json()

    def get(self, **kwargs):
        prepare_headers = {}
        resp = self.session.get(
            url=urljoin(self.gateway, self.api),
            params=kwargs
        )
        return resp.json()


class APIClientMeta(ABCMeta):
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        server_name = cls.__module__.rsplit('.', 1)[-1]
        module_path = f'{server_name}.app'
        used = sys.modules.get(server_name, None)
        module = __import__(module_path).app

        session = requests.Session()

        # 调试模式
        session.proxies = {
            'http': '127.0.0.1:8888',
            'https': '127.0.0.1:8888',
        }

        for route in module.app.routes:
            # 跳过非自定义API路由
            if not isinstance(route, APIRoute):
                continue

            setattr(cls, route.name, APIRequestMethod(
                session=session,
                gateway=get_config(server_name)['gateway'],
                path=route.path,
                methods=route.methods,
                doc=route.endpoint.__doc__,
                description=route.description,
                response_model=route.response_model,
            ))

        if not used:
            # 释放无用的module
            for path in re.finditer(r'\.', module_path):
                del sys.modules[module_path[:path.start()]]
            else:
                del sys.modules[module_path]

