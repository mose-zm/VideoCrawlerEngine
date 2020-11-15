

HOST = '127.0.0.1'


SERVER_CONFIG = {
    'api': {
        'module': 'api.main',
        'entrypoint': 'main',
        'gateway': f'http://{HOST}:2333',
        'host': HOST,
        'port': 2333,
    },
    'taskflow': {
        'module': 'taskflow.main',
        'entrypoint': 'main',
        'gateway': f'http://{HOST}:2332',
        'host': HOST,
        'port': 2332,
    },
    'script': {
        'module': 'script.main',
        'entrypoint': 'main',
        'gateway': f'http://{HOST}:2331',
        'host': HOST,
        'port': 2331,
    },

}


def get_config(server_name):
    return SERVER_CONFIG[server_name]


