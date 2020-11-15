
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, AnyStr, List, Union
from functools import partial


defaultField = partial(Field, default=None)


class NullDataModel(BaseModel):
    pass


class ScriptDataModel(BaseModel):

    url: str = defaultField(title='脚本要处理的目标URL')
    name: str = defaultField(title='脚本处理器名称')
    rule: str = defaultField(title='脚本处理规则')
    quality: str = defaultField(title='质量名称')
    config: Dict[str, Any] = defaultField(title='脚本配置')
    title: str = defaultField(title='脚本唯一标题')
    n: int = defaultField(title='分支数量')


class DownloadDataModel(BaseModel):
    filepath: str = defaultField(title='文件存储路径')
    size: int = defaultField(title='文件大小')


class PayloadJSONDataModel(BaseModel):
    name: str = Field(title='名称')
    type: str = Field(title='类型')
    key: AnyStr = Field(title='识别码')
    data: Union[List, Dict] = Field(title='数据')
