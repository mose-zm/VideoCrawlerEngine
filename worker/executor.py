

from .base import Worker
from concurrent.futures.thread import ThreadPoolExecutor as _ThreadPoolExecutor
from asyncio.runners import _cancel_all_tasks as cancel_all_tasks
from asyncio.base_events import BaseEventLoop
from inspect import iscoroutinefunction
from typing import Callable, Union
from concurrent.futures import Future as threadFuture
from asyncio.futures import Future as asyncFuture
from typing import Any
import asyncio
import sys


def try_async_future(
    future: threadFuture
) -> Union[threadFuture, asyncFuture]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return future
    else:
        return asyncio.wrap_future(future)


class ThreadPoolExecutor(_ThreadPoolExecutor):
    def submit(
        self,
        fn: Callable,
        *args: Any,
        **kwargs: Any
    ) -> threadFuture:
        if self._max_workers == len(self._threads):
            # 如果超过了线程池的承受能力，扩展线程数
            self._max_workers += 1
        return super().submit(fn, *args, **kwargs)


class AsyncPoolExecutor:
    def __init__(self, *args: Any, **kwargs: Any):
        self.loop: BaseEventLoop
        self.executor = ThreadPoolExecutor(max_workers=1)
        # 初始化协程事件循环
        self.executor.submit(self._forever_async_event_loop)

    def _forever_async_event_loop(self) -> None:
        """ 维持一个异步协程事件循环。"""
        if sys.platform == 'win32':
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.get_event_loop()

        asyncio.set_event_loop(loop)
        self.loop = loop
        try:
            loop.run_forever()
        finally:
            try:
                cancel_all_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                loop.close()

    def submit(
        self,
        afunc: Callable,
        *args: Any,
        **kwargs: Any
    ) -> Union[threadFuture, asyncFuture]:
        assert iscoroutinefunction(afunc)
        return asyncio.run_coroutine_threadsafe(
            afunc(*args, **kwargs), self.loop
        )


_COMMON_THREAD_POOL = 0
_COMMON_ASYNC_POOL = 1

_POOL = {
    _COMMON_THREAD_POOL: ThreadPoolExecutor(max_workers=1),
    _COMMON_ASYNC_POOL: AsyncPoolExecutor(max_workers=1),
}


def get_pool(
    worker: Worker
) -> Union[ThreadPoolExecutor, AsyncPoolExecutor]:
    """ 获取工作池。 """
    if worker.meonly:
        # 独占线程
        pool = _POOL.get(id(worker))
        if not pool:
            if worker.async_type:
                pool_cls = AsyncPoolExecutor
            else:
                pool_cls = ThreadPoolExecutor
            pool = pool_cls(max_workers=1)
    else:
        # 获取异步或线程公共池
        if worker.async_type:
            pool = _POOL[_COMMON_ASYNC_POOL]
        else:
            pool = _POOL[_COMMON_THREAD_POOL]
    return pool


def submit(
    worker: Worker,
    *args: Any,
    **kwargs: Any
) -> Union[threadFuture, asyncFuture]:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:

        # if worker.async_type:
        # s = _submit
        # else:
        #     s = _asubmit()
        future = _submit(worker, *args, **kwargs)

    else:
        coro = _asubmit(worker, *args, **kwargs)
        future = asyncio.create_task(coro)
        # if worker.async_type:
        #     s = _asubmit
        # else:
        #     s = _submit
        # s = _asubmit
        # future = s(worker, *args, **kwargs)
        # if isinstance(future, threadFuture):
        #     future = try_async_future(future)
    # if isinstance(future, threadFuture):
    #     future = try_async_future(future)

    return future


def _submit(
    worker: Worker,
    *args: Any,
    **kwargs: Any
) -> Union[threadFuture, asyncFuture]:
    pool = get_pool(worker)
    with worker:
        future = pool.submit(
            worker.entrypoint.run,
            *args,
            **kwargs
        )

    return future


async def _asubmit(
    worker: Worker,
    *args: Any,
    **kwargs: Any
) -> Union[threadFuture, asyncFuture]:
    pool = get_pool(worker)

    async with worker:
        if worker.async_type:
            ep = worker.entrypoint.arun
        else:
            ep = worker.entrypoint.run
        future = pool.submit(
            ep,
            *args,
            **kwargs
        )
        if isinstance(future, threadFuture):
            future = asyncio.wrap_future(future)
        result = await future

    return result

