
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Callable
from functools import partial
from .builtin import defaultField


class ConvertDataModel(BaseModel):
    pass


class FfmpegDataModel(BaseModel):
    cmd: str = defaultField(title='ffmpeg执行命令')
    filepath: str = defaultField(title='输出文件路径')
    input: Callable[..., Dict] = defaultField(title='输入流信息')
    output: Callable[..., Dict] = defaultField(title='输出流信息')


class LiveDataModel(BaseModel):
    
    pass



