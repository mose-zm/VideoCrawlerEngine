from functools import wraps, partial
from inspect import getfullargspec, iscoroutinefunction
from context.contextmgr import context_dict
from context.contexts import progress_mapping_context, request_mapping_context, config_context
from utils.common import current_time
from worker import get_worker, executor
from config import get_config
from traceback import format_exc
from contextlib import contextmanager
from traceback import print_exc
from typing import Any, ClassVar, Optional as typeOptional, AnyStr
from pydantic import BaseModel
from typing import Tuple, List, Callable, Iterator, Union, Dict
from concurrent.futures import Future as threadFuture
from asyncio.futures import Future as asyncFuture
from utils.json import PayloadJSONEncoder, PayloadJSONDecoder
from .model.builtin import PayloadJSONDataModel
import json
import threading

__PAYLOAD_TYPE_NAME__ = {}





class Progress(object):
    """ """

    def __init__(self):
        self.data = {}
        self.logs = []
        self._status = REQ_READY
        self._percent = 0
        self._speed = 0
        self._timeleft = float('inf')

        self.stopmaker = StopMaker()

    @property
    def status(self) -> str:
        status = self._status
        return status() if callable(status) else status

    @status.setter
    def status(self, value):
        self._status = value

    @property
    def percent(self):
        percent = self._percent
        return percent() if callable(percent) else percent

    @percent.setter
    def percent(self, value):
        self._percent = value

    @property
    def speed(self):
        speed = self._speed
        return speed() if callable(speed) else speed

    @speed.setter
    def speed(self, value):
        self._speed = value

    @property
    def timeleft(self):
        timeleft = self._timeleft
        return timeleft() if callable(timeleft) else timeleft

    @timeleft.setter
    def timeleft(self, value):
        self._timeleft = value

    def add_stopper(self, stopper):
        """ 停止器。"""
        self.stopmaker.add_stopper(stopper)

    def stop(self):
        """ """
        if self.status in (REQ_RUNNING, REQ_QUEUING):
            self.stopmaker.run()

    def get_data(self, key, default=None, ignore_safe=True):
        result = self.data.get(key, default)
        if isinstance(result, CallableData):
            result = result()
        elif isinstance(result, (list, tuple, dict, int, str, bytes, set)):
            pass
        elif not ignore_safe:
            result = default
        return result

    def iter_data(self, safe=True):
        if safe:
            return iter([(k, self.get_data(k, ignore_safe=not safe))
                         for k, v in self.data.items()])
        else:
            return iter(self.data)

    def upload(self, **kwargs):
        """ 上传数据。
        :param
            **kwargs:     描述信息
        """
        for k, v in kwargs.items():
            self.data[k] = v

    def enqueue(self):
        self._status = REQ_QUEUING
        self.percent = 0

    def start(self):
        self._status = REQ_RUNNING
        self.percent = 0
        self.timeleft = float('inf')

    def close(self):
        self.stopmaker.destroy()

    def task_done(self):
        if self.status == REQ_RUNNING:
            self._status = REQ_DONE
            self.percent = 100
            self.timeleft = 0

    def error(self, message):
        self._status = REQ_ERROR
        self.report('ERROR: ' + message)

    def success(self, message):
        self.report('SUCCESS: ' + message)

    def info(self, message):
        self.report('INFO: ' + message)

    def warning(self, message):
        self.report('WARNING: ' + message)

    def report(self, message):
        message = current_time() + ' ' + message
        self.logs.append(message)


class Payload(object):
    """ """
    NAME: str
    WEIGHT: int
    TYPE: str
    KEY: AnyStr = b'\x23\x33\x00'

    __locale__: Tuple[int, ...]

    __payloads__: Tuple[Any, ...] = ()

    __args__: Tuple
    __kwargs__: Dict

    def payloads(self) -> Tuple:
        return self.__payloads__

    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    def json(self) -> Any:
        # return json.dumps(dict(PayloadJSONDataModel(
        #     type=self.TYPE,
        #     name=self.NAME,
        #     key=self.KEY,
        #     data={
        #         'args': self.__args__,
        #         'kwargs': self.__kwargs__
        #     }
        # )), cls=PayloadJSONEncoder)

        return json.loads(json.dumps(dict(PayloadJSONDataModel(
            type=self.TYPE,
            name=self.NAME,
            key=self.KEY,
            data={
                'args': self.__args__,
                'kwargs': self.__kwargs__
            }
        )), cls=PayloadJSONEncoder))

    def __new__(cls, *args, **kwargs):
        inst = object.__new__(cls)
        inst.__args__ = args
        inst.__kwargs__ = kwargs
        return inst

    def __init_subclass__(cls, **kwargs):
        # typename = request[task][b'\x23\x33\x32']
        typname = f'{cls.TYPE}[{cls.NAME}]'
        __PAYLOAD_TYPE_NAME__[typname] = cls


class Requester(Payload):
    """ Request 请求对象是用来描述从脚本的开始到完成过程中的处理方式。
    """
    KEY = b'\x23\x33\x01'

    NAME: str = None
    WEIGHT: float
    SIMPLE = None
    TYPE: str = 'request'

    progress: Progress

    # 若__payloads__ == False，则关闭payload搜索。
    __payloads__: typeOptional[tuple] = True

    __info_model__: BaseModel = None

    def start_request(
        self,
        context=None
    ) -> Union[threadFuture, asyncFuture]:
        """ 将请求交给工作线程池进行排队处理。
        在转交工作线程处理之前将当前的上下文环境拷贝一份交给工作线程。
        以保持上下文的连贯性。
        Args；
            context: 该上下文管理器允许
        """
        with enter_requester_context(self):
            ctx = context_dict()
            if context is None:
                context = {}

            ctx.update(context)

            self.progress.enqueue()
            return executor.submit(get_worker(self.NAME), ctx)

    def __call__(self, *args, **kwargs) -> Payload:
        return self

    def end_request(self) -> Any:
        """ 结束请求。"""
        raise NotImplementedError

    def error_handler(self, exception) -> None:
        """ 异常处理。"""
        self.progress.error(format_exc())

    def get_data(self, name, default=None) -> Any:
        result = self.progress.get_data(name, default)
        return result

    def valid_data(self):
        data = {
            k: self.get_data(k)
            for k in self.__info_model__.schema()['properties'].keys()
        }
        return self.__info_model__.construct(**data)

    async def stop(self) -> None:
        return await get_worker('stop').submit(self.progress.stop)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}>'

    def __new__(cls, *args, **kwargs):
        """ 请求对象构建初始化工作。
        1. 创建请求进度对象Progress
        2. 创建进度有效数据模型
        3. 根据需求搜索payloads

        """
        inst = super().__new__(cls, *args, **kwargs)
        inst.progress = Progress()

        if cls.__payloads__ is False:
            payloads = search_payloads(args)
            payloads.extend(search_payloads(kwargs))
            inst.__payloads__ = tuple(payloads)
        else:
            inst.__payloads__ = ()

        return inst

    def __getitem__(self, item):
        return self.get_data(item)

    def upload(self, **kwargs):
        for k, v in kwargs.items():
            self.progress.data[k] = v


def requester(
    request_name: str,
    weight: float = 1,
    root: bool = False,
    info_model: ClassVar[BaseModel] = None,
    no_payload: bool = False,
):
    """ 简单请求构建器。
    Args:
        request_name: 请求者名称
        weight: 当前请求器在百分比percent中所占的权重
        root:
        info_model: 有效数据类型
        no_payload: 是否禁用搜索参数中的payload
    """
    def wrapper(func) -> Callable:
        """ 创建请求器构造器（类）。"""
        (
            argnames,
            varargs,
            varkw,
            defaults,
            kwonlyargs,
            kwonlydefaults,
            annotations
        ) = getfullargspec(func)

        @wraps(func)
        def wrapped(*args, **kwargs) -> Requester:
            """ 请求器参数到实例参数的转接初始化。"""
            _worker = partial(inner, *args, **kwargs)
            kws = {}

            # 设置默认的列表参数
            for i, v in enumerate(
                argnames[len(argnames) - len(defaults or ()):]
            ):
                kws[v] = defaults[i]

            narg = min(len(args), len(argnames))
            # 设置列表参数
            for i in range(narg):
                kws[argnames[i]] = args[i]

            # 关键词转列表参数
            for k in tuple(kwargs):
                if k in argnames:
                    kws[k] = kwargs.pop(k)

            # 设置默认的关键词参数
            for k in kwonlyargs:
                kws[k] = kwargs.pop(k, kwonlydefaults[k])
            # 设置未定义的关键词参数
            kws.update({
                'args': args[narg:],
                'kwargs': kwargs
            })
            req = request_class(**kws)
            req.end_request = _worker

            return req

        # 根据是否协程函数进行处理
        if iscoroutinefunction(func):
            async def inner(*args, **kwargs):
                return await func(*args, **kwargs)
        else:
            def inner(*args, **kwargs):
                return func(*args, **kwargs)

        def __init__(self, **kwargs) -> None:
            """ SIMPLE 请求器初始化函数。"""
            self.args = ()
            self.kwargs = {}
            _ = {self.__setattr__(k, v) for k, v in kwargs.items()}

        def __repr__(self) -> str:
            return f'<{__name__}>'

        __name__ = f'{request_name.title()}Requester'

        class_namespace = {
            'NAME': request_name,
            'WEIGHT': weight,
            'SIMPLE': wrapped,
            '__init__': __init__,
            '__repr__': __repr__,
            '__doc__': func.__doc__,
            '__info_model__': info_model,
            '__payloads__': not no_payload
        }

        if root:
            bases = (RootRequester,)
        else:
            bases = (Requester,)

        request_class = type(__name__, bases, class_namespace)
        return wrapped
    return wrapper


def get_requester(name) -> ClassVar[Requester]:
    """ 返回指定名称的请求器。
    Args:
        name: 请求器名称
    """
    for req_cls in Requester.__subclasses__():
        if name == req_cls.NAME:
            if req_cls.SIMPLE:
                return req_cls.SIMPLE
            else:
                return req_cls
    return None


def get_payload(type, name) -> ClassVar[Payload]:
    """ """
    return __PAYLOAD_TYPE_NAME__.get(f'{type}[{name}]', None)


def search_payloads(arg) -> List[Union[List[Requester], List[List], Requester]]:
    """ 迭代搜索请求的payload。"""
    def search_array(o) -> None:
        """ 搜索 list, tuple, set迭代对象。"""
        for v in o:
            if isinstance(v, Payload):
                payloads.append(v)
            else:
                goto_search(v)

    def search_dict(o) -> None:
        """ 搜索字典。"""
        for k, v in o.items():
            if isinstance(k, Payload):
                payloads.append(k)
            else:
                goto_search(k)

            if isinstance(v, Payload):
                payloads.append(v)
            else:
                goto_search(v)

    def goto_search(o) -> None:
        """ 迭代搜索。注意在交叉嵌套的情况下会出现无限迭代的问题。
        但事实上payload通常不存在交叉嵌套的情况。
        """
        if isinstance(o, (list, tuple, set)):
            search_array(o)
        elif isinstance(o, dict):
            search_dict(o)
        elif isinstance(o, Payload):
            payloads.append(o)

    payloads = []
    goto_search(arg)
    return payloads


class StopMaker(object):
    """ 请求制动器。
    执行请求器添加的停止器。若没有提供停止器，则一直等待请求结束。
    """
    def __init__(self) -> None:
        self.stopper_lst = []
        self.sema = threading.Semaphore(0)

    def run(self) -> None:
        with self.sema:
            for stopper in self.stopper_lst:
                try:
                    stopper()
                except Exception:
                    print_exc()

    def add_stopper(self, stopper) -> None:
        """ 仅允许非协程函数作为停止器。
        如果是协程函数，使用functools.partial(asyncio.run, stopper())来实现
        """
        assert not iscoroutinefunction(stopper)
        assert callable(stopper)
        self.stopper_lst.append(stopper)
        self.sema.release()

    def destroy(self) -> None:
        with self.sema._cond:
            self.sema._value = float('inf')
            self.sema._cond.notify_all()


class Optional(Payload):
    NAME = 'optional'
    TYPE = 'optional'

    KEY = b'\x23\x33\x02'

    def __init__(self, options) -> None:
        """
        :param
            list:       可选择的项列表
            sort_key:   项目排序的key
        """
        self._options = options
        self._selected = None

    def __iter__(self) -> Iterator:
        return iter(self._options)

    @property
    def selected(self):
        """ 返回被选择的项。"""
        if self._selected is None:
            raise ValueError('未选择的列表。')
        return self._selected

    def select(self, rule):
        """ 根据rule来选择最恰当的选项。
        :param
            rule:   选择规则
                - high:     最高质量 100
                - middle:   中等质量 50
                - low:      最低质量 1
                - %d:       1-100   [1,100] - (注意: 倾向于高质量。)
        """
        if rule == 'high':
            rule = 100
        elif rule == 'low':
            rule = 1
        elif rule == 'middle':
            rule = 50

        if isinstance(rule, int) and 1 <= rule <= 100:
            selected = self._options[
                max(0, int((100-rule) * len(self._options) / 100) - 1)]
        else:
            selected = self._options[0]
        self._selected = selected
        return selected

    def __getattr__(self, item):
        return getattr(self._selected, item)

    def __repr__(self):
        return repr(self._selected)

    def __call__(self, rule, *args, **kwargs):
        if not self._selected:
            self.select(rule)
        return self._selected()


class Option(Payload):
    NAME = 'option'
    TYPE = 'option'

    KEY = b'\x23\x33\x03'

    def __init__(self, content, descriptions=None):
        self._content = content
        if descriptions is None:
            descriptions = {}
        self.descriptions = descriptions

    def __repr__(self):
        return str(self._content)

    def __getattr__(self, item):
        return getattr(self._content, item)

    def __call__(self, *args, **kwargs):
        return self._content()


class Sequence(Payload):
    """ """
    NAME = 'sequence'
    TYPE = 'sequence'
    KEY = b'\x23\x33\x04'

    def __init__(self, *seqs):
        self.sequences = seqs

    def __iter__(self):
        return iter(self.sequences)

    def __len__(self):
        return len(self.sequences)

    def payloads(self):
        return self.sequences

    def __call__(self, *args, **kwargs):
        return self.sequences


REQ_READY = 'ready'
REQ_QUEUING = 'queuing'
REQ_RUNNING = 'running'
REQ_STOPPED = 'stopped'
REQ_WARNING = 'warning'
REQ_ERROR = 'error'
REQ_DONE = 'done'


class RootRequester(Requester):
    NAME = 'root'


def unpack_payloads(
    syntax: Payload,
    rule
) -> Tuple[List[Requester], List[RootRequester]]:
    """ 序列化节点项
    Args:
        syntax:
        rule:
    """
    def call_syntax(o):
        """ payload根据规则rule处理。"""
        if not isinstance(o, Payload):
            raise TypeError(f'非定义语法: {type(o)}')
        return o(rule)

    def lookup_payload(o):
        """ 建立工作流串并行链。"""
        # payload
        o = call_syntax(o)

        # root请求器优先，如果存在就抛弃其他请求
        if isinstance(o, RootRequester):
            srp.append(o)
            return None

        # 为了兼容Sequence方法，所有o都以列表的形式迭代处理。
        if not isinstance(o, (list, tuple)):
            o = [o]

        s = []
        for i in o:
            for req in i.payloads():
                # 处理payloads里的请求 
                r = lookup_payload(req)
                
                # 如果返回的是None是因为该请求属于root请求，
                # 这将屏蔽所有的请求
                if r is None:
                    return None
                s.extend(r)

        # 请求的payload + 原请求对象，
        # 完成先处理payloads再到处理请求
        if s:
            return [s] + o

        return o

    srp = []
    flow = lookup_payload(syntax)
    return flow, srp


@contextmanager
def enter_requester_context(
    request: Requester
):
    """  """
    with progress_mapping_context.enter(request.progress), \
         request_mapping_context.enter(request), \
         config_context.enter(dict(get_config(request.NAME))):
        yield


class CallableData(partial):
    pass


callable_data = CallableData


