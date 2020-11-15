

from context.contextmgr import ContextManager
from contextlib import contextmanager

__scope__ = ContextManager('__scope__')

__debug_mode__ = False
__path__ = None


@contextmanager
def run(context):
    """ 运行"""
    global __scope__
    with __scope__.enter(context):
        yield __scope__


class DebugChain:
    def __init__(self, prename, name):
        self.__prename__ = prename
        self.__name__ = name

    def __getattr__(self, item):
        prename = [self.__prename__] if self.__prename__ else []
        obj_chain = f'{".".join(prename + [self.__name__, item])}'
        try:
            obj = _lookup_scope(obj_chain)
            return obj
        except (KeyError, LookupError):
            return DebugChain(f'{".".join(prename + [self.__name__])}', item)

    def __repr__(self):
        return f'<DebugChain {self.__str__()}>'

    def __str__(self):
        prename = [self.__prename__] if self.__prename__ else []
        return ".".join(prename + [self.__name__])

    def __len__(self):
        return len(__scope__.get())

    def __call__(self, *args, **kwargs):
        raise LookupError(f'找不到对象链: {self.__str__()}')


def __getattr__(name):
    try:
        return _lookup_scope(name)
    except (KeyError, LookupError):
        return DebugChain('', name)


def _lookup_scope(chain):
    return __scope__[chain]


@contextmanager
def run_in_debug_mode(**options):
    from worker import init_workers
    from config import load_config
    from task import TaskStack

    global __debug_mode__
    load_config()
    init_workers()
    __debug_mode__ = True

    task = TaskStack(None)
    yield task

