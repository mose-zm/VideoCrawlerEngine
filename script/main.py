from . import init_scripts
from config import HOST
from worker import register_worker
from worker.entrypoint import get_ep
from requester.config import get_config
from .app import app
import uvicorn

_GLOBAL_WORKER = 'script'


def init_worker():
    script_config = get_config('script')
    register_worker(
        _GLOBAL_WORKER,
        script_config['max_concurrent'],
        script_config.get('async', False),
        script_config.get('meonly', False),
        get_ep(script_config.get('entrypoint', 'request')),
    )


def main():
    init_scripts()
    init_worker()
    config = get_config('script')
    uvicorn.run(app, host=HOST, port=2331)

