
from requester import requester
from . import Requester, unpack_payloads
from taskflow.layer.flow import make_payload_exec_layer
from typing import Callable
from context import debugger as dbg
from worker import get_worker, executor
from .__engine__ import Payload
from typing import Optional, Any
import asyncio
from traceback import format_exc, print_exc


@requester('live', no_payload=True)
async def live_daemon(
    live_getter: Callable[[], Payload] = None,
):
    """ 直播录像服务。
    """
    heartbeat_interval = dbg.glb.script['heartbeat'] or 10
    while True:
        try:
            # payload = await get_worker('keep-live').submit(live_getter)
            payload = await executor.submit(get_worker('keep-live'), live_getter)
            # 更新脚本数据
            dbg.glb.script.upload(
                title=dbg.get_data('title'),
            )

            lay = make_payload_exec_layer(payload)
            await lay.run()
        except:
            print_exc()

        await asyncio.sleep(heartbeat_interval)

