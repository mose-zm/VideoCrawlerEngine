from pydantic import Field
from pydantic.main import BaseModel
from typing import List, Dict, Union


class TaskCreateParams(BaseModel):
    pass


class StopTaskParams(BaseModel):
    pass


class TaskCreateParams(BaseModel):
    pass


class CreateTaskParams(BaseModel):
    pass




class GetSupportedParams(BaseModel):
    url: str = Field(title='URL链接')


class GetVersionsParams(BaseModel):
    name: str = Field(title='查询的脚本名称')


class RegisterParams(BaseModel):
    path: str = Field(title='脚本路径')
    sha256: str = Field(title='脚本文件SHA256')


class CallScriptParams(BaseModel):
    url: str = Field(title='URL链接')
    rule: Union[str, int] = Field(title='脚本处理规则')
    extra: Dict = Field(title='额外字段参数', default={})


class ExecuteScriptParams(BaseModel):
    name: str = Field(title='脚本名称，带版本号后可忽略version参数')
    version: str = Field(title='脚本版本号，可在name后带版本号.', default=None)

    # url: str = Field(title='URL链接')
    # rule: Union[str, int] = Field(title='脚本处理规则')
    kwargs: CallScriptParams = Field(title='脚本调用参数')

