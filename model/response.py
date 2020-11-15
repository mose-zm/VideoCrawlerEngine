from typing import List, Dict

from pydantic import Field

from model.base import APIRespModel
from model.data import ScriptModel


class GetSupportedResp(APIRespModel):
    data: List[ScriptModel] = Field(title='支持的脚本')


class GetVersionsResp(APIRespModel):
    data: List[ScriptModel] = Field(title='脚本')


class RegisterResp(APIRespModel):
    pass


class ExecutorScriptResp(APIRespModel):
    data: List[Dict] = Field(title='脚本执行响应。')