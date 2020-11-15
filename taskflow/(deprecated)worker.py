from concurrent.futures.thread import ThreadPoolExecutor
# from config import get_config, SECTION_WORKER
from config.script import get_config, SECTION_WORKER
from entrypoint import get_entrypoint
from utils.common import cancel_all_tasks
from contexts import glb
import threading
import asyncio
import sys

# 工作者平台
REGISTERED_WORKER = {}

WORKER_ENTRYPOINT = {}


# class AsyncExecutorPool:
#     def __init__(self, max_workers):
#         self.max_workers = max_workers
#         self.pool = ThreadPoolExecutor(
#             max_workers=max_workers,
#             initializer=self._setup_async_event_loop
#         )
#         self._using_loop = set()
#         self._setup_lock = threading.Lock()
#         self._setup_event = threading.Event()
#
#     def acquire(
#         self,
#         max_worker,
#         alone,
#     ):
#         pass
#
#     def _setup_async_event_loop(self):
#         with self._setup_lock:
#             if sys.platform == 'win32':
#                 loop = asyncio.ProactorEventLoop()
#             else:
#                 loop = asyncio.get_event_loop()
#
#             asyncio.set_event_loop(loop)
#             # loop = loop
#             # 初始化完成事件
#             self._setup_event.set()
#             del ready_evt
#
#             self._sema = asyncio.Semaphore(max_workers)
#         try:
#             loop.run_forever()
#         finally:
#             try:
#                 cancel_all_tasks(loop)
#                 loop.run_until_complete(loop.shutdown_asyncgens())
#             finally:
#                 loop.close()
#
#     def _adjust_thread_pool(self):
#         pass
#
#
# class ExecutorPool:
#     def __init__(self):
#         self.thread_count = 0
#         self.pool = ThreadPoolExecutor(
#
#         )
#
#
#
# __pool = {
#     'async': ThreadPoolExecutor,
#     'thread': AsyncExecutorPool
# }
#
#
# def get_pool(type):
#     """ 获取线程池。"""
#     return 1
#
#
# class Worker:
#     def __init__(
#         self,
#         max_workers,
#         type,
#         alone=False,
#     ):
#         self.max_workers = max_workers
#         self.type = type
#         self.alone = alone
#         self.handle = None
#
#     def submit(self, *args, **kwargs):
#
#         pool = get_pool(self.type)



class Workers:
    __type__: str

    def __init__(self, name, max_workers, entrypoint=None, *args, **kwargs):
        self.name = name
        self.max_workers = max_workers
        self.entrypoint = entrypoint

    def submit(self):
        raise NotImplementedError

    # def run(self):
    #     raise NotImplementedError

    def shutdown(self, wait=True):
        pass


class NullWorkers(Workers):
    __type__ = 'null'

    def submit(self, *args, **kwargs):
        # return self.run(*args, **kwargs)
        with glb['worker'].enter(self):
            return get_entrypoint(self.entrypoint, False)(*args, **kwargs)

    # def run(self, *args, **kwargs):
    #     with glb['worker'].enter(self):
    #         return get_entrypoint(self.entrypoint, False)(*args, **kwargs)

    def shutdown(self, wait=True):
        pass


class AsyncNullWorkers(Workers):
    __type__ = 'null async'

    @property
    def loop(self):
        return asyncio.get_running_loop()

    def submit(self, *args, **kwargs):
        # return self.run(*args, **kwargs)
        with glb['worker'].enter(self):
            return get_entrypoint(self.entrypoint, True)(*args, **kwargs)

    # def run(self, *args, **kwargs):
    #     with glb['worker'].enter(self):
    #         return get_entrypoint(self.entrypoint, True)(*args, **kwargs)

    def shutdown(self, wait=True):
        pass


def try_async_future(future):
    """ 尝试将线程concurrent.futures.Future封装成异步asyncio.futures.Future。"""
    try:
        loop = asyncio.get_running_loop()
        return asyncio.wrap_future(future, loop=loop)
    except RuntimeError:
        return future


class ThreadWorkers(Workers):
    """ 工作线程"""
    __type__ = 'thread'

    def __init__(self, name, max_workers, entrypoint=None, *, initializer=None, initargs=()):
        Workers.__init__(self, name, max_workers, entrypoint)
        self.workers = ThreadPoolExecutor(
            max_workers, thread_name_prefix=name,
            initializer=initializer, initargs=initargs)

    def submit(self, *args, **kwargs):
        """ 提交工作任务。"""
        # return try_async_future(
        #     self.workers.submit(self.run, *args, **kwargs)
        # )
        with glb['worker'].enter(self):
            return try_async_future(
                self.workers.submit(get_entrypoint(self.entrypoint, False), *args, **kwargs)
            )

    # def run(self, *args, **kwargs):
    #     with glb['worker'].enter(self):
    #         return get_entrypoint(self.entrypoint, False)(*args, **kwargs)

    def shutdown(self, wait=True):
        return self.workers.shutdown(wait)


class AsyncWorkers(Workers):
    __type__ = 'async'

    def __init__(self, name, max_workers, entrypoint=None, *args, **kwargs):
        def setup_async_thread():
            nonlocal ready_evt
            if sys.platform == 'win32':
                loop = asyncio.ProactorEventLoop()
            else:
                loop = asyncio.get_event_loop()

            asyncio.set_event_loop(loop)
            self.loop = loop
            # 初始化完成事件
            ready_evt.set()
            del ready_evt

            self._sema = asyncio.Semaphore(max_workers)
            try:
                loop.run_forever()
            finally:
                try:
                    cancel_all_tasks(loop)
                    loop.run_until_complete(loop.shutdown_asyncgens())
                finally:
                    loop.close()

        if max_workers is None:
            # 未限制的异步行为
            max_workers = float('inf')

        super().__init__(name, 1, entrypoint)
        self.loop = None
        self.max_workers = max_workers
        self._sema = None
        self.workers = ThreadPoolExecutor(
            max_workers, thread_name_prefix=name)
        ready_evt = threading.Event()
        self.workers.submit(setup_async_thread)
        ready_evt.wait()

    def submit(self, *args, **kwargs):
        coro = get_entrypoint(self.entrypoint, True)(*args, **kwargs)
        return try_async_future(
            asyncio.run_coroutine_threadsafe(self.run(coro, *args, **kwargs), self.loop)
        )

    async def run(self, coro, *args, **kwargs):
        with glb['worker'].enter(self):
            async with self._sema:
                # return await get_entrypoint(self.entrypoint, True)(*args, **kwargs)
                return await coro

    def shutdown(self, wait=True):
        self.loop.call_soon_threadsafe(self.loop.stop)
        super().shutdown(wait)


def setup_worker(name, config):
    def get_workers_cls(type_name):
        for subcls in Workers.__subclasses__():
            if subcls.__type__ == type_name:
                return subcls
        raise TypeError('没有找到对应类型的Worker处理器。')

    global REGISTERED_WORKER
    max_concurrent = config['max_concurrent']
    # is_async = config.get('async', False)
    # if is_async:
    #     if max_concurrent is None or max_concurrent < 1:
    #         workers_cls = AsyncNullWorkers
    #     else:
    #         workers_cls = AsyncWorkers
    # else:
    #     if max_concurrent is None or max_concurrent < 1:
    #         workers_cls = NullWorkers
    #     else:
    #         workers_cls = ThreadWorkers
    workers_cls = get_workers_cls(config['type'])

    entrypoint = config.get('entrypoint', 'request')
    # entrypoint = get_entrypoint(config.get('entrypoint', 'request'), is_async)
    REGISTERED_WORKER[name] = workers_cls(name, max_concurrent, entrypoint)


def init_workers():
    """ 初始化工作者们。 """
    global REGISTERED_WORKER

    workers = get_config(SECTION_WORKER)

    for k, v in workers.items():
        setup_worker(k, v)


def get_worker(name):
    """ 返回指定名称的工作者。"""
    global REGISTERED_WORKER
    return REGISTERED_WORKER.get(name)


def shutdown_all():
    global REGISTERED_WORKER
    for k, v in REGISTERED_WORKER.items():
        v.shutdown(False)


def shutdown(name, wait=True):
    get_worker(name).shutdown(wait)


def restart(name):
    get_worker(name).shutdown(True)
    setup_worker(name, get_config(SECTION_WORKER))


def forever_async_loop():
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.get_event_loop()

    asyncio.set_event_loop(loop)
    self.loop = loop
    # 初始化完成事件
    ready_evt.set()
    del ready_evt

    self._sema = asyncio.Semaphore(max_workers)
    try:
        loop.run_forever()
    finally:
        try:
            cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()


# class WorkerPool:
#     def __init__(self):
#
#         self.threadpool = ThreadPoolExecutor(
#             max_workers=1,
#             thread_name_prefix='threadpool_',
#         )
#         self.asyncpool = ThreadPoolExecutor(
#             max_workers=1,
#             thread_name_prefix='asyncpool_',
#             initializer=forever_async_loop
#         )
#
#
#     async def async_submit(self):
#         pass
#
#     def submit(self):
#         pass
#
#     def shutdown_all(self):
#         """ 关闭所有线程。"""
#
#
