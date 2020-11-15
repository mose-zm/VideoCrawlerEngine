from typing import List

from pydantic import Field
from pydantic.main import BaseModel


class ScriptModel(BaseModel):
    name: str = Field(title='名称')
    version: str = Field(title='版本号')
    supported_domains: List[str] = Field(title='支持的域名')
    author: str = Field(title='作者')
    created_date: str = Field(title='创建日期')
    license: str = Field(title='许可证')
    qn_ranking: List = Field(title='质量排序')