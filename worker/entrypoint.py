from traceback import print_exc
from context import debugger as dbg
from context.contextmgr import context_dict


__EPS__ = {}


class Entrypoint:
    NAME: str

    def run(self, *args, **kwargs):
        raise NotImplementedError

    async def arun(self, *args, **kwargs):
        raise NotImplementedError

    def __init_subclass__(cls, **kwargs):
        if cls.NAME in __EPS__:
            raise ValueError(f'存在重名的entrypoint -> {cls.NAME}')
        __EPS__[cls.NAME] = cls


class SubmitEntrypoint(Entrypoint):
    NAME = 'submit'

    def __init__(self):
        self.context = context_dict()

    def run(self, func, *args, **kwargs):
        with dbg.run(self.context):
            try:
                result = func(*args, **kwargs)
            except Exception:
                print_exc()
                raise
            return result

    async def arun(self, func, *args, **kwargs):
        with dbg.run(self.context):
            try:
                result = await func(*args, **kwargs)
            except Exception:
                print_exc()
                raise
            return result


class RequesterEntrypoint(Entrypoint):
    NAME = 'request'

    def run(self, context):
        with dbg.run(context) as debug:
            try:
                debug.start()
                result = debug.end_request()
                debug.task_done()
            except BaseException as err:
                print_exc()
                debug.error_handler(err)
                raise
            finally:
                debug.close()
        return result

    async def arun(self, context):
        with dbg.run(context) as debug:
            try:
                debug.start()
                result = await debug.end_request()
                debug.task_done()
            except BaseException as err:
                print_exc()
                dbg.error_handler(err)
                raise
            finally:
                debug.close()

        return result


def get_ep(name):
    """ 返回入口点。"""
    ep_cls = __EPS__.get(name, None)
    if ep_cls is None:
        raise ValueError(f'找不到名称为{name}的入口点。')
    ep = ep_cls()
    return ep
