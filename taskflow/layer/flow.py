import asyncio

from context import debugger as dbg
from context.contexts import d, b, local, flow, e
from requester import unpack_payloads
from requester.__engine__ import Payload
from taskflow.layer.base import BaseLayer
from taskflow.layer.work import WorkLayer


class ParallelLayer(BaseLayer):
    """ 并行工作流层。
    """
    def __init__(self, depth, flows, sema=None, is_head=False):
        self.depth = depth

        # 可并行的分支流
        self.flows = [_unwrap_parallel_flows(depth, f) for f in flows]
        self.sema = sema
        self.is_head = is_head

    def __iter__(self):
        return iter(self.flows)

    def __len__(self):
        return len(self.flows)

    async def stop(self):
        return await asyncio.wait([f.stop() for f in self.flows])

    def locale(self, mark_branch_index=False):
        """ """

        def _serial_locale(f, index):
            with d.enter(index):
                if self.is_head:
                    with b.enter(index):
                        return f.locale()
                else:
                    return f.locale()

        for i, f in enumerate(self.flows):
            _serial_locale(f, i)

    async def run(self):
        async def _serial_worker(f, index):
            try:
                async with sema:
                    with local['__task__'].enter(tasks[index]):
                        return await f.run()
            except BaseException as err:
                # 某一条分支发生异常，如果这是头并行层，也就是分支并行层，
                # 进行额外的处理。
                if not self.is_head:
                    # 非分支并行层，不对异常做处理
                    raise
                raise

        sema = self.sema
        if not sema:
            sema = asyncio.Semaphore(float('inf'))
        tasks = [asyncio.create_task(_serial_worker(f, i)) for i, f in enumerate(self.flows)]
        done, pending = await asyncio.wait(
            tasks,
            # 某一条分支出现错误没必要取消所有的分支
            return_when=asyncio.FIRST_EXCEPTION if not self.is_head else asyncio.ALL_COMPLETED
        )

        # TODO: 在这里需要找出是哪一个节点发生的异常。

        # 当某一个节点出现异常的时候，取消所有的任务
        for unfinished_task in pending:
            unfinished_task.cancel()

        if pending:
            # 等待所有的任务停止, 然后抛出任务节点异常
            _, pending = await asyncio.wait(pending)

            done = done.union(_)
        for dn in done:
            try:
                dn.result()
            except Exception as e:
                raise RuntimeError('某一个节点发生异常导致任务停止。') from e

    def __repr__(self):
        return f'<ParallelLayer depth={self.depth}>'


class SerialLayer(BaseLayer):
    """ 串行工作流层
    在串行层中，以所有”节点“处于同一层级。这里面的”节点“包括了以并行层作为整体的节点。
    """
    def __init__(self, depth, flows):
        self.depth = depth

        # 串行的工作流
        self.flows = [_unwrap_serial_flows(depth, f) for f in flows]

        # 任务取消状态
        self._cancelled = False

    def __iter__(self):
        return iter(self.flows)

    def __len__(self):
        return len(self.flows)

    def __getitem__(self, item):
        if not isinstance(item, int):
            raise TypeError()
        return self.flows[item]

    async def stop(self):
        self._cancelled = True
        return await asyncio.wait([f.stop() for f in self.flows])

    async def run(self):
        l = None
        try:
            # 在该层中未初始化的情况下，这里 __layer__ 的值是上一层的值
            lastl = flow['__layer__'].get()
        except LookupError:
            lastl = None

        for i, f in enumerate(self.flows):
            if self._cancelled:
                raise PermissionError('任务中止。')
            if len(self.flows) >= i + 1:
                n = None
            else:
                n = self.flows[i+1]
            with flow['__layer__'].enter(self), \
                 flow['last'].enter(l), flow['next'].enter(n), \
                 flow['last_layer'].enter(lastl):
                await f.run()
            l = f

    def locale(self):
        for i, f in enumerate(self.flows):
            with e.enter(i):
                f.locale()

    def __repr__(self):
        return f'<SerialLayer depth={self.depth}>'


def _unwrap_serial_flows(depth, flow):
    """ 打开串行层中的工作流。"""
    if isinstance(flow, (list, tuple)):
        # 串行层的下一层是并行层
        return ParallelLayer(depth + 1, list(flow))
    else:
        return WorkLayer(depth, flow)


def _unwrap_parallel_flows(depth, flow):
    """ 打开并行层中的工作流。"""
    if isinstance(flow, (list, tuple)):
        # 并行层的下一层是串行层
        return SerialLayer(depth, list(flow))
    else:
        #
        return WorkLayer(depth, flow)


def make_payload_exec_layer(
    payload: Payload
):
    """"""

    f, s = unpack_payloads(payload, dbg.glb.script['rule'])
    lay = SerialLayer(0, f)
    lay.locale()
    return lay