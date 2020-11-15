import os
from collections import defaultdict
from urllib.parse import urlparse

import bs4
import requests

from context import debugger as dbg
from context.contextmgr import context_dict
# from script import default_config, get_config, REGISTERED_SCRIPT
from script.config import get_config, default_config, REGISTERED_SCRIPT, iter_config
from utils.common import split_name_version


# from . import supplied_utilities
from utils.common import utility_package

# 已编译的脚本仓库

# 注册的域
# 'example.com': 'name-version'


class ScriptBaseClass(object):
    name: str = None

    @classmethod
    def test(cls, url, rule=None, config=None, *args, **kwargs):
        """ 构建脚本调试环境，并调用脚本的run方法，
        最后返回由该脚本构成的脚本请求ScriptRequest。"""
        from .base import ScriptBaseClass
        from requester import script_request
        from requester import enter_requester_context

        class TestScript(cls, ScriptBaseClass):
            # 继承base.py基类
            pass

        if config is None:
            config = get_config(TestScript.name) or default_config()

        script = ScriptTask(TestScript, config)
        # 打开调试模式
        dbg.__set_debug__ = True
        request = script_request(url, rule=rule, script_cls=script)
        with enter_requester_context(request), dbg.run(context_dict()):
            dbg.start()
            result = request.end_request()
            dbg.task_done()
            dbg.close()
        return request


# 脚本仓库
repository = {}
registered_domains = defaultdict(list)

# 提供给脚本的第三方库
supplied_utilities = {
    'ScriptBaseClass': ScriptBaseClass,
    'requests': requests,
    'bs4': bs4,
    'dbg': dbg,
}
# 提供给脚本的第三方库
supplied_utilities.update(utility_package)


class ScriptTask:
    """ 脚本任务。 """
    def __init__(self, script_cls, config=None):
        """
        :param
            script:     脚本类对象
            config:     脚本执行配置
        """
        self.script_cls = script_cls
        self.config = config or default_config()

    def __call__(self, url, quality=None, **kwargs):
        script_cls = self.script_cls
        config = self.config
        return script_cls(config, url, quality, **kwargs)

    @property
    def name(self):
        return self.script_cls.name

    @property
    def version(self):
        return self.script_cls.version

    @property
    def supported_domains(self):
        return self.script_cls.supported_domains

    @property
    def quality_ranking(self):
        return self.script_cls.quality_ranking

    @property
    def author(self):
        return self.script_cls.author

    @property
    def created_date(self):
        return self.script_cls.created_date

    def __repr__(self):
        return '<ScriptTask %s==%s>' % (self.script_cls.name, self.script_cls.version)


class Scripts:
    """ 编译的脚本。"""
    def __init__(self, name):
        """
        :param
            name:       脚本名称。
        """
        self.name = name
        self.scripts = {}
        self._active = None
        self.config = get_config(name) or default_config()

    @property
    def supported_domains(self):
        """ 返回active脚本所支持的域。"""
        return self._active.supported_domains

    @property
    def version(self):
        """ 返回active脚本的版本号。"""
        return self._active.version

    def get(self, version=None):
        """ 返回指定版本的脚本。"""
        if version is None:
            version = self.version
        script = self.scripts.get(version, None)
        if script is None:
            return None
        return ScriptTask(script, dict(self.config))

    def install(self, script):
        """ 安装已编译的脚本。
        注意：若安装了更高版本的脚本，将会自动更改激活新的版本。所以若要使用低版本，
        需要在安装新脚本后重新激活旧版本的脚本。
        """
        self.scripts[script.version] = script
        if not self._active or script.version > self._active.version:
            self.active(script.version)

    def active(self, version):
        """ 激活指定版本的脚本。"""
        if version not in self.scripts:
            raise ValueError('找不到版本号: %s。' % version)
        self._active = self.scripts[version]

    def get_versions(self):
        """ 返回该脚本所有的版本号。"""
        return sorted(self.scripts.keys(), reverse=True)

    def __repr__(self):
        return '<Script %s==%s>' % (self.name, self.version)

    def __iter__(self):
        return iter(self.scripts.items())


def validate_script(source_byte, key):
    """ 脚本sha256校验。"""
    from hashlib import sha256
    s = sha256()
    s.update(source_byte)
    if s.hexdigest() != key:
        return None
    return source_byte


def compile_script(script_name, verify=True):
    """ 编译指定脚本。"""
    with open(os.path.join(os.path.realpath('.'), 'script', script_name), 'rb') as fb:
        source = fb.read()
    # 脚本校验。
    if verify and not validate_script(source, REGISTERED_SCRIPT.get(script_name, None)):
        return PermissionError('脚本校验未通过。')
    # 脚本编译
    code = compile(source, '<string>', 'exec')
    # 脚本全局作用域
    _globals = supplied_utilities.copy()
    # 脚本执行得到的作用域
    scope = {}
    try:
        exec(code, _globals, scope)
    except Exception as err:
        from traceback import print_exc
        print_exc()
        return err
    else:
        global repository, registered_domains, ScriptBaseClass
        # 从脚本中提取爬虫继承类。
        for k, v in scope.items():
            try:
                if issubclass(v, ScriptBaseClass):
                    if not v.name:
                        continue
                    # 保存编译的脚本
                    if v.name not in repository:
                        repository[v.name] = Scripts(v.name)
                    repository[v.name].install(v)

                    # DOC: https://docs.python.org/zh-cn/3.7/library/stdtypes.html#code-objects
                    # 代码对象被具体实现用来表示“伪编译”的可执行 Python 代码，例如一个函数体。
                    # 它们不同于函数对象，因为它们不包含对其全局执行环境的引用。
                    v.run.__globals__.update(scope)
                    # 域-脚本 映射。
                    for domain in v.supported_domains:
                        registered_domains[domain.rstrip('/')].append(f'{v.name}:{v.version}')
            except TypeError as e:
                # 非继承ScriptBaseClass，跳过检测
                continue
    return None


def select_script(scripts):
    """ 该方法会返回列表中优先级最高的脚本。"""
    def latest_version(name_version):
        return (get_config(split_name_version(name_version)[0]) or {'order': 0})['order']
    return max(scripts, key=latest_version)


def get_script(script_name, version=None):
    """ 返回已经编译好的爬虫脚本对象。
    :param
        script_name:脚本名称。若脚本名称带有版本号，那么将返回指定版本号的脚本，否则返回被激活的脚本。
        version:    若None获取最新的版本。
    """
    name, _version = split_name_version(script_name)
    if _version is not None:
        version = _version

    script = repository.get(name, None)
    if not script:
        # 没有找到指定名称的脚本。
        return None
    return script.get(version)


def get_versions(script_name):
    """ 返回指定名称脚本含有的所有版本。"""
    versions = repository.get(script_name, None)
    if not versions:
        return None
    return sorted(versions, reverse=True)


def supported_script(url):
    """ 返回能处理该URL的脚本名称-版本。
    :param
        url:            提供要处理的URL。
        with_version:   返回名称是否带有版本号。
    """
    netloc = urlparse(url).netloc
    result = []
    for k, v in registered_domains.items():
        if netloc.endswith(k):
            result.extend(v)
    return result


def register(script_name, sha256_key):
    """ 注册爬虫脚本。 """
    if not os.path.isfile('script/%s' % script_name):
        raise FileNotFoundError('在脚本目录script下未找到指定名称的脚本，请检查是否存在该文件。')

    if script_name in REGISTERED_SCRIPT:
        raise PermissionError('该脚本已注册，请不要重复注册。')

    REGISTERED_SCRIPT[script_name] = sha256_key


def init_scripts():
    """ 脚本初始化。"""
    global ScriptBaseClass
    # 初始化爬虫脚本基类
    compile_script('base.py', verify=False)
    # 更新base.py的默认使用版本
    version = get_config('base')['active']
    try:
        version = float(version)
    except (TypeError, ValueError):
        version = None
    if version is not None:
        repository['base'].active(version)
    # 准备脚本基类。
    ScriptBaseClass = get_script('base').script_cls
    supplied_utilities['ScriptBaseClass'] = ScriptBaseClass

    # 编译所有注册的脚本。
    for script in [filename for filename in REGISTERED_SCRIPT.keys() if filename != 'base.py']:
        compile_script(script, False)

    # 加载脚本配置
    for k, v in iter_config().items():
        if k is None or k == 'null':
            continue
        script = repository.get(k, None)
        try:
            active_version = float(v['active'])
        except (TypeError, ValueError):
            active_version = None
        if script and active_version is not None:
            # 激活配置中的默认信息。
            script.active(active_version)