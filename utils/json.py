

from json.encoder import JSONEncoder
from json.decoder import JSONDecoder, WHITESPACE
from typing import Any, Callable
from base64 import b64encode, b64decode
import json

JSON_BYTES_PREFIX = 'data:any/any;base64,'


class PayloadJSONEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        from requester.__engine__ import Payload, get_requester, get_payload
        print(type(o), o)
        if isinstance(o, Payload):
            result = o.json()
            return result
        elif isinstance(o, bytes):
            return f"data:any/any;base64,{b64encode(o).decode('utf-8')}"
        return JSONEncoder.default(self, o)


class PayloadJSONDecoder(JSONDecoder):
    def decode(self, s, _w=WHITESPACE.match) -> Any:
        result = super().decode(s, _w)
        return build_payloads_object(result)


def build_payloads_object(o):
    def payload_json(i):
        from requester.__engine__ import Payload, get_requester, get_payload

        payload_cls = get_payload(i['type'], i['name'])
        # req_cls = get_requester(i['name'])
        if payload_cls is None:
            raise ValueError(f'找不到名称为{i["name"]}的{i["type"]}。')
        args = type_to(i['data']['args'])
        kwargs = type_to(i['data']['kwargs'])
        return payload_cls(*args, **kwargs)

    def type_to(i):
        if isinstance(i, dict):
            key = i.get('key', None)
            if key:
                if key.startswith(JSON_BYTES_PREFIX):
                    key = b64decode(key[len(JSON_BYTES_PREFIX):])
                if key.startswith(b'\x23\x33'):
                    return payload_json(i)
            return {k: type_to(v) for k, v in i.items()}
        elif isinstance(i, list):
            return [type_to(v) for v in i]
        return i

    return type_to(o)
