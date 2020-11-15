from taskflow.layer.base import BaseLayer
from context.contexts import c, a, b, d, e, f, glb, abcdef, local
from context import debugger as dbg


class WorkLayer(BaseLayer):
    """ 工作层。"""
    def __init__(self, depth, work):
        self.depth = depth

        self.work = work

    def __len__(self):
        return 1

    def __iter__(self):
        return iter([self.work])

    # async def locale(self):
    #     with c.enter(self.depth):
    #         try:
    #             # 如果不发生异常说明了该脚本以进行中，
    #             # 那么这一层只能作为子层来进行处理
    #             _ = dbg.glb.script
    #             # abcde以当前工作节点为父节点
    #             self.work.__locale__ = (
    #                 dbg.a,
    #                 dbg.b,
    #                 dbg.c,
    #                 dbg.d,
    #                 dbg.e,
    #                 (b(), c(), d(), e())
    #             )
    #         except:
    #             self.work.__locale__ = (
    #                 a(),
    #                 b(),
    #                 c(),
    #                 d(),
    #                 e(),
    #                 f()
    #             )
    #         glb['task']().add_work(self.work)

    def locale(self):
        with c.enter(self.depth):
            try:
                # 如果不发生异常说明了该脚本以进行中，
                # 那么这一层只能作为子层来进行处理
                dbg.glb.script()
                # abcde以当前工作节点为父节点
                self.work.__locale__ = (
                    dbg.a,
                    dbg.b,
                    dbg.c,
                    dbg.d,
                    dbg.e,
                    (b(), c(), d(), e())
                )
            except LookupError:
                self.work.__locale__ = (
                    a(),
                    b(),
                    c(),
                    d(),
                    e(),
                    f()
                )
            glb['task']().add_work(self.work)

    async def run(self):
        _a, _b, _c, _d, _e, _f = self.work.__locale__
        with a.enter(_a), b.enter(_b), c.enter(_c), d.enter(_d), e.enter(_e), f.enter(_f), \
             abcdef.enter(self.work.__locale__), local['request'].enter(self.work), \
             glb['task']():
            # return await self.work.start_request()
            return await self.work.start_request()

    async def stop(self):
        await self.work.stop()

    def __repr__(self):
        return f'<WorkLayer depth={self.depth}>'

    @property
    def type(self):
        type_names = [v for k, v in {
            # Requester: 'request',
            # While: 'dowhile',
            # Loop: 'loop',
            object: 'unknown',
        }.items() if isinstance(self.work, k)]
        if not type_names or type_names[0] == 'unknown':
            raise TypeError()
        return type_names[0]