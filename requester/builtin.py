import threading

from context.contexts import a, b
from taskflow.layer.script import ScriptLayer
from requester import (requester)
from utils.common import safety_filename
# from script import select_script, supported_script, get_script, ScriptBaseClass
# from client.script import get_client
from nbdler import Request as DlRequest, dlopen, HandlerError
from typing import List, Optional, Dict, Union

from . import Requester
from .model.builtin import ScriptDataModel, DownloadDataModel
from context import debugger as dbg
import time
import asyncio
import os


@requester('jsruntime')
def jsruntime(session, **kwargs):
    """ """
    session.leave()


@requester('cleanup', weight=0.3)
def cleanup():
    """ 清楚临时文件。 """
    dbg.tempdir.rmfiles(True)


@requester('download', weight=1, info_model=DownloadDataModel)
async def download(
    uri: str = None,
    headers: Dict = None,
    *,
    multi_sources: List[Dict] = None,
    **kwargs
):
    """ 下载请求
    Args:
        uri: 下载uri
        headers: 指定下载请求头
        multi_sources: 多下载源的添加方式。
            [{'uri': 'http://xxx', 'headers': headers}, ...]

    """
    # 创建下载请求对象
    tempf = dbg.tempdir.mktemp()
    dlr = DlRequest(file_path=tempf)
    sources = []
    if uri:
        sources = [{
            'uri': uri,
            'headers': headers,
            **kwargs
        }]
    sources += multi_sources or []

    for source in sources:
        dlr.put(**source)

    async with dlopen(dlr) as dl:
        dbg.upload(
            size=dl.file.size,
            filepath=dl.file.pathname,
        )
        dbg.set_percent(dl.percent_complete)
        dbg.set_timeleft(dl.remaining_time)
        dbg.set_speed(lambda: dl.transfer_rate())

        dl.start(loop=asyncio.get_running_loop())
        # FIX: Nbdler 下载器在协程下出现的问题
        while not dl._future:
            await asyncio.sleep(0.01)

        # 创建下载停止器
        dbg.add_stopper(dl.pause)

        async for exception in dl.aexceptions():
            dbg.warning(exception.exc_info)
            if isinstance(exception, HandlerError):
                await dl.apause()
                break
        else:
            exception = None
        await dl.ajoin()

    if exception:
        # 若发生异常，抛出异常
        raise exception from exception.exception

    # 更新文件信息
    dbg.upload(
        filepath=dl.file.pathname,
        size=dl.file.size,
    )


@requester('script', root=True, info_model=ScriptDataModel)
def fake_script(
    request_items: List[Requester],
    rule: str or int,
    **options
):
    """ (调试模式) 调试模式下的虚假脚本请求Root。"""
    from script import ScriptTask, ScriptBaseClass

    url = 'http://fake.script'
    script = ScriptTask(ScriptBaseClass)('')
    dbg.upload(
        url=url,
        name=script.name,
        script=script,
        rule=rule,
        quality=100,
        title=f'debug_{time.time() * 1000}',
        tempdir=dbg.glb.config['tempdir'],
        n=1,
        config=script.config,
    )
    dbg.upload(**options)
    dbg.upload(items=[request_items])
    return dbg.get_data('items')


@requester('script', root=True, info_model=ScriptDataModel)
def simple_script(
    url: str,
    rule: Optional[Union[str, int]],
    script_cls,
    *,
    allow_child_script: bool = False,
    **kwargs
):
    if rule is None:
        rule = script_cls.config.get('default_rule')
    qn = script_cls.quality_ranking
    quality = qn[max(0, round((100 - int(rule)) * len(qn) / 100) - 1)]

    # 请求来源脚本请求
    dbg.upload(
        url=url,
        name=script_cls.name,
        script=script_cls,
        rule=rule,
        quality=quality,
        config=script_cls.config,
    )

    # 创建并运行脚本
    script_cls(
        url=url,
        quality=quality,
        allow_child_script=allow_child_script,
        **kwargs
    ).run()

    # title = safety_filename(dbg.get_data('title', ''))
    #
    # # 创建临时目录
    # tempdir = os.path.realpath(os.path.join(
    #     dbg.glb.config['tempdir'],
    #     script_cls.name,
    #     title,
    # ))
    #
    # items = dbg.get_data('items', [])
    # if not items:
    #     item = dbg.get_data('item', [])
    #     if item:
    #         items = [item]
    #
    # dbg.upload(
    #     title=title,
    #     # tempdir=tempdir,
    #     n=len(items),
    # )
    #
    # return items
    return dbg.get_data('items', [])


@requester('script', root=True, info_model=ScriptDataModel)
def script_request(
    url: str,
    rule: Optional[Union[str, int]] = None,
    script_cls=None,
    *,
    allow_child_script: bool = False,
    **kwargs
):
    """
    Args:
        url: 目标URL
        rule: 选择规则
        script_cls: 预加载脚本，若提供将直接使用该脚本构造器
        allow_child_script: 是否允许子脚本请求
        
    """
    if script_cls is None:
        name = select_script(supported_script(url))
        script_cls = get_script(name)
        script_cls = script_cls

    if rule is None:
        rule = script_cls.config.get('default_rule')
    qn = script_cls.quality_ranking
    quality = qn[max(0, round((100 - int(rule)) * len(qn) / 100) - 1)]

    # 请求来源脚本请求
    dbg.upload(
        url=url,
        name=script_cls.name,
        script=script_cls,
        rule=rule,
        quality=quality,
        config=script_cls.config,
    )

    # 创建并运行脚本
    script_cls(
        url=url,
        quality=quality,
        allow_child_script=allow_child_script,
        **kwargs
    ).run()

    title = safety_filename(dbg.get_data('title', ''))

    # 创建临时目录
    tempdir = os.path.realpath(os.path.join(
        dbg.glb.config['tempdir'],
        script_cls.name,
        title,
    ))

    items = dbg.get_data('items', [])
    if not items:
        item = dbg.get_data('item', [])
        if item:
            items = [item]

    dbg.upload(
        title=title,
        tempdir=tempdir,
        n=len(items),
    )

    return items


@requester('misc_async')
async def sleep(delay=None):
    """ 睡眠等待。"""
    if delay is None:
        delay = dbg.glb.script['config'].get('delay', 5)
    await asyncio.sleep(delay)


@requester('task')
async def start_task(
    url: str,
    rule: Union[int, str] = None,
    **options
):
    """ 创建任务的起点：

    """
    async def _worker(index, layer):
        # 定位工作层节点并编号
        with a.enter(index):
            layer.locale()

            async with sema:
                return await layer.run()

    s = get_script(
        select_script(supported_script(url))
    )

    script_req = script_request(
        url=url,
        rule=rule,
        script_cls=s,
        allow_child_script=False
    )

    scriptlay = ScriptLayer(script_req)

    with a.enter(0):
        subscripts = await scriptlay.execute_script()

    dbg.upload(
        title=script_req.get_data('title'),
        url=script_req.get_data('url'),
    )

    max_workers = 1
    sema = asyncio.Semaphore(max_workers)
    tasks = [
        asyncio.create_task(_worker(i, s))
        for i, s in enumerate([scriptlay] + subscripts)
    ]

    dbg.add_stopper(scriptlay.stop)
    return await asyncio.wait(tasks)


class FakeTask(Requester):
    """ fake task for debugging."""
    NAME = 'task'

    def __init__(self, **fake_script_options):
        self._queue = None
        self._ready = threading.Event()
        self.fake_script_options = fake_script_options
        self.loop = None

    async def end_request(self):
        async def _worker(layer, index):
            with b.enter(index):
                await layer.locale()

                async with sema:
                    return await layer.run()

        self._queue = asyncio.Queue()
        self._ready.set()
        self.loop = asyncio.get_running_loop()
        acnt = 0
        while True:
            data, options = await self._queue.get()
            with a.enter(acnt):
                rule = options.get('rule', 1)
                options['rule'] = rule

                script = ScriptLayer(fake_script(data, **options))
                await script.execute_script()

                tasks = [
                    asyncio.create_task(_worker(s, i))
                    for i, s in enumerate([script])
                ]

                max_workers = 3
                sema = asyncio.Semaphore(max_workers)

                dbg.add_stopper(script.stop)
                await asyncio.wait(tasks)
                self._queue.task_done()
            acnt += 1

    def run(self, o, **options):
        self._ready.wait(timeout=10)
        asyncio.run_coroutine_threadsafe(self._queue.put((o, options)),
                                         loop=self.loop)