

from fastapi import APIRouter, Depends, FastAPI
from model.param import (
    GetSupportedParams,
    GetVersionsParams,
    RegisterParams,
    ExecuteScriptParams
)
from model.response import (
    GetSupportedResp,
    GetVersionsResp,
    RegisterResp,
    ExecutorScriptResp
)
from model.data import (
    ScriptModel
)
from . import get_script, get_versions as script_versions, supported_script, register
from worker import executor, get_worker
from requester import simple_script

script_router = APIRouter()
stack_router = APIRouter()


@script_router.get(
    '/getSupported',
    response_model=GetSupportedResp
)
async def get_supported(
    params: GetSupportedParams = Depends(GetSupportedParams),
):
    scripts = supported_script(params.url)
    data = [ScriptModel(
        name=s.name,
        version=s.version,
        author=s.author,
        created_date=s.created_date,
        qn_ranking=s.quality_ranking,
        license=s.license,
    ) for s in scripts]
    return GetSupportedResp(data=data)


@script_router.get(
    '/getVersions',
    response_model=GetVersionsResp
)
async def get_versions(
    params: GetVersionsParams = Depends(GetVersionsParams)
):
    scripts = script_versions(params.name)
    data = [ScriptModel(
        name=s.name,
        version=s.version,
        author=s.author,
        created_date=s.created_date,
        qn_ranking=s.quality_ranking,
        license=s.license,
        supported_domains=s.supported_domains,
    ) for s in [ns[1] for ns in scripts]]
    return GetVersionsResp(data=data)


@script_router.post(
    '/register',
    response_model=RegisterResp
)
async def register(
    params: RegisterParams = Depends(RegisterParams),
):
    pass


@script_router.post(
    '/exec',
    response_model=ExecutorScriptResp
)
async def exec_script(
    params: ExecuteScriptParams,
):
    script_cls = get_script(params.name, params.version)
    req = simple_script(
        url=params.kwargs.url,
        rule=params.kwargs.rule,
        script_cls=script_cls
    )
    # req = script_request(
    #     url=params.url,
    #     rule=params.rule,
    #     script_cls=script_cls
    # )
    result = await req.start_request()
    # await executor.submit(
    #     get_worker('script'),
    #
    # )
    data = [r.json() for r in result]
    print(data)
    print(data)
    print(result)
    return ExecutorScriptResp(data=data)


@stack_router.post(
    '/destroy',

)
async def destroy_stack(
    params,
):
    """ 销毁脚本缓存栈。"""


@stack_router.post(
    '/exec'
)
async def exec_stack(
    params,
):
    """ 执行脚本栈中函数。"""




def include_routers(app: FastAPI) -> None:
    app.include_router(
        script_router,
        prefix='/script'
    )

