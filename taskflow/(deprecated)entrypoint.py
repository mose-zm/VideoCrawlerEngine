from traceback import print_exc
# from inspect import iscoroutinefunction
from context import debugger as dbg
from contextmgr import context_dict


# __ENTRYPOINT = {}
#
# __ASYNC_ENTRYPOINT = {}

ENTRYPOINT = {}


class Entrypoint:
    NAME: str

    def run(self, *args, **kwargs):
        raise NotImplementedError

    async def arun(self, *args, **kwargs):
        raise NotImplementedError

    def __init_subclass__(cls, **kwargs):
        if cls.NAME in ENTRYPOINT:
            raise ValueError(f'存在重名的entrypoint -> {cls.NAME}')
        ENTRYPOINT[cls.NAME] = cls


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


def get_entrypoint(name, async_type):
    """ 返回入口点。"""
    ep_cls = ENTRYPOINT.get(name, None)
    if ep_cls is None:
        raise ValueError(f'找不到名称为{name}的入口点。')
    ep = ep_cls()
    return ep.arun if async_type else ep.run


# def entrypoint(name):
#     def wrapper(func):
#         if iscoroutinefunction(func):
#             # @wraps(func)
#             # async def wrapped(*args, **kwargs):
#             #     return await func(*args, **kwargs)
#             # __ASYNC_ENTRYPOINT[name] = wrapped
#             __ASYNC_ENTRYPOINT[name] = func
#             # return wrapped
#             return func
#         else:
#             # @wraps(func)
#             # def wrapped(*args, **kwargs):
#             #     return func(*args, **kwargs)
#             # __ENTRYPOINT[name] = wrapped
#             # return wrapped
#             __ENTRYPOINT[name] = func
#             return func
#     return wrapper
#
#
# @entrypoint('request')
# async def async_request_entrypoint(context):
#     with dbg.run(context) as debug:
#         try:
#             debug.start()
#             result = await debug.end_request()
#             debug.task_done()
#         except BaseException as err:
#             print_exc()
#             dbg.error_handler(err)
#             raise
#         finally:
#             debug.close()
#
#     return result
#
#
# @entrypoint('request')
# def request_entrypoint(context):
#     """ 请求任务处理入口点。 """
#     with dbg.run(context) as debug:
#         try:
#             debug.start()
#             result = debug.end_request()
#             debug.task_done()
#         except BaseException as err:
#             print_exc()
#             debug.error_handler(err)
#             raise
#         finally:
#             debug.close()
#     return result
#
#
# @entrypoint('submit')
# def submit_entrypoint(func, *args, **kwargs):
#     """ """
#     # with dbg.run(context):
#     try:
#         result = func(*args, **kwargs)
#     except Exception:
#         print_exc()
#         raise
#     return result
#
#
# @entrypoint('submit')
# async def async_submit_entrypoint(func, *args, **kwargs):
#     """ """
#     # with dbg.run(context):
#     try:
#         result = await func(*args, **kwargs)
#     except Exception:
#         print_exc()
#         raise
#     return result
#
#
# def get_entrypoint(name, async_type):
#     """ 返回入口点。"""
#     if async_type:
#         entrypoints = __ASYNC_ENTRYPOINT
#     else:
#         entrypoints = __ENTRYPOINT
#
#     return entrypoints[name]
#
