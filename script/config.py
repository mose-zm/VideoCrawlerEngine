

REGISTERED_SCRIPT = {
    # 'base.py': '',
    'bilibili.py': '',
}


__SCRIPT_CONFIG__ = {
    'base': {
        # 脚本优先级, 数值越小，优先级越高
        # 当多个脚本能够解析同一个域的时候，使用优先级高的脚本进行处理。
        'order': 100,
        'cookies': '',
        'proxies': None,
        'active': None,
        'default_rule': 1,
        'to_format': ['.mp4'],
        'starter': ['start'],
        'append': ['convert', 'cleanup'],
        'remove_tempdir': True,
    },
    'fake': {
        'order': 9999,
        'cookies': '',
        'proxies': None,
        'active': None,
        'default_rule': 1,
        'target_format': ['.mp4'],
        'append': ['convert', 'cleanup'],
        'rm_tempdir': True,
    },
    # global 全局配置
    None: {
        'tempdir': '',
        'to_format': '.mp4',
        'savedir': '',
    }
}


def default_config():
    """ 默认脚本配置。"""
    return {
        'order': 100,
        'cookies': '',
        'proxies': None,
        'active': None,
        'default_rule': 1,
        'to_mimetype': ['.mp4'],
        'append': ['convert', 'cleanup'],
        'storage_dir': '',
        'remove_tempdir': True,
        'error_handler': ['error']
    }


def get_config(name):
    global __SCRIPT_CONFIG__

    return __SCRIPT_CONFIG__.get(name, None)


def iter_config():
    return __SCRIPT_CONFIG__


def setup_config():
    pass


def load_config():
    pass
