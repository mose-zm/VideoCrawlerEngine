import asyncio
import worker
from traceback import print_exc
from context import debugger as dbg
from context.contexts import glb, b, tempdir
from taskflow.layer.flow import ParallelLayer
from taskflow.layer.base import BaseLayer
from requester import unpack_payloads, get_requester
from requester.utils.tempfile import TemporaryDir


class ScriptLayer(BaseLayer):
    def __init__(self, script):
        self.depth = 0

        self.script = script

        self.subscripts = None
        self.flows = None

    def __len__(self):
        return len(self.flows)

    def __iter__(self):
        return iter(self.flows or [])

    async def execute_script(self):
        try:
            all_items = await self.script.start_request()
        except Exception as e:
            print_exc()
            raise
        subscripts = []
        subflows = []
        with glb['script'].enter(self.script):
            for index, item in enumerate(all_items):
                with b.enter(index):
                    f, s = unpack_payloads(item, self.script['rule'])

                    if not dbg.__debug_mode__:
                        extra_flows = [
                            get_requester(name)()
                            for name in self.script.get_data('config', {}).get('append', [])
                        ]
                        f.extend(extra_flows)
                    subflows.append(f)
                    subscripts.extend(ScriptLayer(s))

            self.flows = ParallelLayer(1, subflows, is_head=True)
            self.subscripts = subscripts

        return subscripts

    # async def locale(self):
    #     """"""
    #     await self.flows.locale(mark_branch_index=True)

    def locale(self):
        """"""
        self.flows.locale(mark_branch_index=True)

    async def run(self, reload=False):
        if not self.flows and not self.subscripts:
            await self.execute_script()

        with glb['script'].enter(self.script), \
             tempdir.enter(TemporaryDir(self.script.get_data('tempdir'))):

            return await self.flows.run()

    def stop(self):
        asyncio.run(asyncio.wait([f.stop() for f in self.flows]))
        # 重启stop worker线程，避免过多的线程滞留
        worker.restart('stop')