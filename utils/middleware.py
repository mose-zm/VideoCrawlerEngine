
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from exception import (
    APIBaseError,
)
from codetable import VALIDATE_ERROR


async def api_exception_handler(
    request: Request,
    exc: APIBaseError
):
    return JSONResponse(
        status_code=200,
        content=dict(
            code=exc.code,
            msg=exc.msg,
            data=exc.data
        ),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    return JSONResponse(
        status_code=418,
        content=dict(
            code=VALIDATE_ERROR,
            msg='参数检查不通过。',
            data=[]
        ),
    )


def include_exception_handler(app: FastAPI) -> None:
    """ 异常处理器。"""
    app.exception_handler(APIBaseError)(api_exception_handler)
    app.exception_handler(RequestValidationError)(validation_exception_handler)
