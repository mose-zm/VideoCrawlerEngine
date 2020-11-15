

from context.contextmgr import ContextManager, ContextNamespace, ObjectMappingContext

# 主编号
a = ContextManager('a', default=0)

# 分支号
b = ContextManager('b', default=0)

# 深度
c = ContextManager('c', default=0)

# 工作流编号
d = ContextManager('d', default=0)

# 节点编号
e = ContextManager('e', default=0)

# 子节点编号
f = ContextManager('f', default=())


abcdef = ContextManager('abcdef', default=(a(), b(), c(), d(), e(), f()))

a4f = abcdef

tempdir = ContextManager('tempdir', default='')


# local
local = ContextNamespace('local', )
local.contextmanager('__task__')
local.contextmanager('request')
local.contextmanager('__layer__')

# global 全局属性
glb = ContextNamespace('glb')
glb.globalcontext('config')
glb.contextmanager('script')
glb.contextmanager('info')
glb.contextmanager('task')
glb.contextmanager('worker')
# dbg.local.script

# glb.contextmanager('test')

# flow
# flow = ContextManager('flow')
flow = ContextNamespace('flow')

flow.contextmanager('__layer__')
flow.contextmanager('next')
flow.contextmanager('last')

flow.contextmanager('next_layer')
flow.contextmanager('last_layer')

#
progress_mapping_context = ObjectMappingContext(
    attrs='percent speed timeleft status',
    meths='upload start close task_done get_data error success info warning report add_stopper stop'
)
request_mapping_context = ObjectMappingContext(
    meths='end_request error_handler'
)
config_context = ContextManager('config', {})

